# app.py
"""Main Flask application for the SMS gateway."""
import uuid
from flask import Flask, jsonify, render_template, request, current_app
from flask_socketio import SocketIO, emit
from threading import Lock, Thread
from modem_handler import ModemHandler
from auth import AuthManager, require_auth
from config import Config
import logging
import json
import time
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("SUPABASE_DB_NAME"),
    "user": os.getenv("SUPABASE_DB_USER"),
    "password": os.getenv("SUPABASE_DB_PASSWORD"),
    "host": os.getenv("SUPABASE_DB_HOST"),
    "port": os.getenv("SUPABASE_DB_PORT", "5432")  # Default to 5432 if not provided
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*")




# Global variables
thread = None
thread_lock = Lock()
modem_handler = None

def handle_sms_callback(sms):
    """Handle incoming SMS messages."""
    logger.info("SMS received from: %s", sms.number)
    
    data = {
        "number": sms.number,
        "time": sms.time.isoformat(),
        "text": sms.text
    }
    
    socketio.emit('sms_web', json.dumps(data), namespace='/', broadcast=True)
    logger.info("SMS data emitted to websocket")

def additional_sms_processing(sms):
    """Additional SMS processing if needed."""
    logger.info("Processing SMS in additional callback")

def initialize_modem():
    try:
        logger.info("Initializing modem...")
        handler = ModemHandler(
                    config=Config,
                    socketio=socketio,  # Pass the socketio instance
                    sms_callback=additional_sms_processing  # Optional
                )
        
        # Try to connect
        if not handler.connect():
            logger.error("Failed to connect to modem")
            return None
            
        # Wait for network
        if not handler.wait_for_network():
            logger.error("Failed to register with network")
            return None
            
        # Check network status
        status_ok, message = handler.check_network_status()
        if not status_ok:
            logger.error("Network status check failed: %s", message)
            return None
            
        logger.info("Modem initialized successfully: %s", message)
        return handler
        
    except Exception as e:
        logger.error("Error initializing modem: %s", str(e), exc_info=True)
        return None

try:
    modem_handler = None
    max_init_attempts = 3
    
    for attempt in range(max_init_attempts):
        logger.info("Attempting modem initialization (attempt %d/%d)", 
                   attempt + 1, max_init_attempts)
        
        modem_handler = initialize_modem()
        if modem_handler:
            break
            
        logger.warning("Initialization attempt failed, retrying in 5 seconds...")
        time.sleep(5)
        
    if not modem_handler:
        logger.error("Failed to initialize modem after %d attempts", max_init_attempts)
except Exception as e:
    logger.error("Critical error during modem initialization: %s", str(e), exc_info=True)

# # Initialize ModemHandler with SMS callback
# modem_handler = ModemHandler(
#     config=Config,
#     socketio=socketio,  # Pass the socketio instance
#     sms_callback=additional_sms_processing  # Optional



auth_manager = AuthManager(modem_handler, Config.SECRET_KEY)

@app.route('/')
def index():
    """Serve the frontend interface."""
    return render_template('index.html')


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.close()
        conn.close()
        return jsonify({"status": "success", "message": "Database connection successful"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/send_sms', methods=['POST'])
def send_sms():
    """API endpoint to send SMS messages."""
    try:
        data = request.json
        number = data.get('number')
        message = data.get('message')

        if not number or not message:
            return jsonify({
                'status': 'error',
                'message': 'Phone number and message are required.'
            }), 400

        modem_handler.send_sms(number, message)
        return jsonify({
            'status': 'success',
            'message': 'SMS sent successfully'
        })

    except Exception as e:
        logger.error("Failed to send SMS: %s", str(e))
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/send_ussd', methods=['POST'])
def send_ussd():
    """API endpoint to send USSD commands."""
    try:
        data = request.json
        ussd_code = data.get('ussd_code')

        if not ussd_code:
            logger.error("USSD code missing in request")
            return jsonify({
                'status': 'error',
                'message': 'USSD code is required.'
            }), 400

        logger.info("Received USSD request with code: %s", ussd_code)
        response = modem_handler.send_ussd(ussd_code)
        
        logger.info("USSD response: %s", response)
        try:
            # Emit with namespace and error handling
            socketio.emit('ussd_response', 
                         {'response': response.get('response')},
                         namespace='/',
                         broadcast=True)
            logger.info("USSD response emitted successfully")
        except Exception as e:
            logger.error("Failed to emit USSD response: {}".format(str(e)))
        
        return jsonify(response)

    except Exception as e:
        logger.error("Failed to send USSD command: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/forward_sms', methods=['POST'])
def forward_sms():
    """Receive SMS data from modem_handler and emit to frontend."""
    try:
        data = request.json
        socketio.emit('sms_grab', data, namespace='/')
        return jsonify({'status': 'SMS forwarded successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/send-code', methods=['POST'])
def send_verification():
    """Send verification code to phone number."""
    logger.info("=== New verification code request ===")
    
    # Log raw request data
    logger.debug("Request headers: %s", dict(request.headers))
    logger.debug("Request method: %s", request.method)
    logger.debug("Request content type: %s", request.content_type)
    
    try:
        # Log raw request body
        logger.debug("Raw request body: %s", request.get_data())
        
        # Parse JSON
        data = request.get_json(force=True)  # force=True will help debug malformed JSON
        logger.info("Parsed request data: %s", data)
        
        if not data:
            logger.error("No JSON data in request")
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400
        
        # Get phone number
        phone_number = data.get('phone_number')
        logger.info("Extracted phone number: %s", phone_number)
        
        if not phone_number:
            logger.warning("Missing phone number in request data")
            return jsonify({
                'status': 'error',
                'message': 'Phone number is required'
            }), 400
        
        # Check auth_manager
        if not auth_manager:
            logger.error("auth_manager is None")
            return jsonify({
                'status': 'error',
                'message': 'Authentication service not available'
            }), 503
            
        # Send verification code
        logger.info("Calling auth_manager.send_verification_code...")
        result = auth_manager.send_verification_code(phone_number)
        logger.info("Result from send_verification_code: %s", result)
        
        # Check result
        if result.get('status') == 'error':
            logger.error("Error from send_verification_code: %s", 
                        result.get('message'))
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        logger.error("=== Error in send_verification ===")
        logger.error("Error type: %s", type(e).__name__)
        logger.error("Error message: %s", str(e))
        logger.error("Traceback:", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error: {}'.format(str(e))
        }), 500

@app.route('/auth/verify-code', methods=['POST'])
def verify_code():
    """Verify the code sent to phone number."""
    logger.info("Received code verification request")
    try:
        data = request.json
        logger.debug("Request data: %s", data)
        
        phone_number = data.get('phone_number')
        code = data.get('code')
        
        if not phone_number or not code:
            logger.warning("Missing phone number or code in request")
            return jsonify({
                'status': 'error',
                'message': 'Phone number and code are required'
            }), 400
            
        logger.info("Verifying code for %s", phone_number)
        result = auth_manager.verify_code(phone_number, code)
        logger.info("Verification result: %s", result)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error verifying code: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    
def parse_sms(sms_text):
    """
    Parse MVola SMS with support for both French and Malagasy formats.
    """
    # Define patterns for both languages
    french_pattern = r"""
        ^(?P<amount>\d+(?:\s*\d+)*)\s*Ar\s*    # Amount with optional spaces
        recu\s+de\s+                           # Transaction indicator (French)
        (?P<name>[^(]+)                        # Name (everything until opening parenthesis)
        \((?P<phone>\d+)\)\s*                  # Phone number in parentheses
        le\s+
        (?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{2})\s*  # Date
        a\s+(?P<hour>\d{2}):(?P<minute>\d{2})   # Time
        .*?                                    # Non-greedy match for optional reason/server text
        Solde\s*:\s*                          # Balance indicator
        (?P<balance>\d+(?:\s*\d+)*)\s*Ar      # Balance amount
        .*?                                    # Non-greedy match for any text
        Ref:\s*(?P<reference>\d+)             # Reference number
        """

    malagasy_pattern = r"""
        ^Nahazo\s+                            # Transaction indicator (Malagasy)
        (?P<amount>\d+(?:\s*\d+)*)\s*Ar\s*    # Amount
        avy\s+any\s+amin['']ny\s+             # From indicator
        (?P<name>[^(]+)                        # Name
        \((?P<phone>\d+)\)\s*                  # Phone number
        ny\s+
        (?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{2})\s+  # Date
        (?P<hour>\d{2}):(?P<minute>\d{2})      # Time
        .*?                                    # Non-greedy match for reason
        Ny\s+volanao\s+dia\s+                 # Balance indicator
        (?P<balance>\d+(?:\s*\d+)*)\s*Ar      # Balance
        .*?                                    # Non-greedy match
        Ref:\s*(?P<reference>\d+)             # Reference
        """
    
    match = re.search(french_pattern, sms_text, re.VERBOSE | re.IGNORECASE)
    if not match:
        match = re.search(malagasy_pattern, sms_text, re.VERBOSE | re.IGNORECASE)
    
    if match:
        try:
            # Extract all matched groups as a dictionary
            result = match.groupdict()
            
            # Clean up amounts by removing spaces
            for key in ['amount', 'balance']:
                if result.get(key):
                    result[key] = int(re.sub(r'(\d)\s+(\d)', r'\1\2', result[key]))
            
            # Format datetime
            date_str = "{}-{}-{} {}:{}:00".format(
                result['year'], result['month'], result['day'],
                result['hour'], result['minute']
            )
            date_obj = datetime.strptime(date_str, '%y-%m-%d %H:%M:%S')
            
            # Create the final parsed data matching the database schema
            parsed_data = {
                "raw_message": sms_text,
                "type": "in",  # All examples are incoming transactions
                "amount": result['amount'],
                "name": result['name'].strip(),
                "phone": result['phone'],
                "date_time": date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                "balance": result['balance'],
                "reference": result['reference'],
                "correspondent_type": "Remitter"  # Since all examples are incoming
            }
            
            logger.info("Successfully parsed: %s", parsed_data)
            return parsed_data
            
        except Exception as e:
            logger.error("Error parsing matched groups: %s", str(e))
            return None
    else:
        logger.info("No match found for SMS")
        return None

@app.route('/raw-sms', methods=['POST'])
def handle_raw_sms():
    """Handle raw SMS data."""
    try:
        data = request.json
        logger.info("Received data: %s", data)
        
        if not data or "message" not in data:
            return jsonify({'status': 'error', 'message': 'No SMS data provided'}), 400

        raw_sms = data['message']
        parsed_sms = parse_sms(raw_sms)
        
        if not parsed_sms:
            # Store unparsed SMS with minimal data
            sms_data = {
                "raw_message": raw_sms,
                "date_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            sms_data = parsed_sms

        logger.info("Sending to Supabase: %s", sms_data)

        # Use Supabase config from Config class
        supabase_url = app.config['SUPABASE_API_URL']
        supabase_key = app.config['SUPABASE_API_KEY']

        if not supabase_url.endswith('/mobile_money_sms'):
            supabase_url = "{}/mobile_money_sms".format(supabase_url)

        response = requests.post(
            supabase_url,
            json=sms_data,
            headers={
                "apikey": supabase_key,
                "Authorization": "Bearer {}".format(supabase_key),
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
        )
        
        if response.status_code not in [200, 201]:
            logger.error("Supabase error: Status %d, Response: %s", response.status_code, response.text)
            return jsonify({
                'status': 'error',
                'message': 'Supabase error: {}'.format(response.text),
                'sent_data': sms_data
            }), response.status_code
        else:
            logger.info("Successfully saved to Supabase: Status %d", response.status_code)

        message = "SMS successfully parsed and saved" if parsed_sms else "SMS saved without parsing"
        return jsonify({'status': 'success', 'message': message, 'data': sms_data}), 200

    except Exception as e:
        logger.error("Error handling SMS: %s", str(e), exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
ussd_sessions = {}  # Store active USSD sessions

@app.route('/api/ussd/start', methods=['POST'])
def start_ussd_session():
    """Start a new USSD session"""
    try:
        session_id = str(uuid.uuid4())
        data = request.json
        initial_code = data.get('code', '#111#')
        
        ussd_sessions[session_id] = {
            'status': 'active',
            'step': 0,
            'history': []
        }
        
        socketio.emit('ussd_request', {
            'type': 'ussd_request',
            'code': initial_code,
            'session_id': session_id
        })
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'response': 'Waiting for USSD response...',
            'message': 'USSD request sent'
        })
    except Exception as e:
        logger.error("Error starting USSD session: %s", str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/ussd/continue', methods=['POST'])
def continue_ussd_session():
    """Continue an existing USSD session"""
    try:
        data = request.json
        session_id = data.get('session_id')
        user_input = data.get('input')
        
        if not session_id or session_id not in ussd_sessions:
            return jsonify({'status': 'error', 'message': 'Invalid session'}), 400
            
        socketio.emit('ussd_request', {
            'type': 'ussd_request',
            'code': user_input,
            'session_id': session_id
        })
        
        return jsonify({
            'status': 'success',
            'message': 'USSD request sent'
        })
    except Exception as e:
        logger.error("Error in USSD session: %s", str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@socketio.on('ussd_response')
def handle_ussd_response(data):
    """Handle USSD response from Flutter app"""
    session_id = data.get('session_id')
    if session_id in ussd_sessions:
        # Forward response to frontend
        emit('ussd_response', {
            'session_id': session_id,
            'response': data.get('response'),
            'requires_input': data.get('requires_input', True)
        }, broadcast=True)

@app.route('/protected-resource')
@require_auth(auth_manager)
def protected_resource():
    """Example of a protected endpoint."""
    logger.info("Protected resource accessed by %s", request.user_phone)
    return jsonify({
        'message': "Hello {0}! This is a protected resource.".format(request.user_phone)
    })

def background_worker():
    """Background worker to maintain modem connection and process stored SMS."""
    while True:
        try:
            if not modem_handler.modem:
                modem_handler.connect()
            modem_handler.process_stored_sms()
        except Exception as e:
            logger.error("Background worker error: %s", str(e))
            try:
                modem_handler.disconnect()
            except:
                pass
        time.sleep(Config.SMS_PROCESS_INTERVAL)

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    global thread
    with thread_lock:
        if thread is None:
            thread = Thread(target=background_worker)
            thread.daemon = True
            thread.start()
    logger.info("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    logger.info("Client disconnected")

if __name__ == '__main__':
    try:
        socketio.run(
            app,
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG
        )
    finally:
        if modem_handler:
            modem_handler.disconnect()