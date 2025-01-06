# app.py
"""Main Flask application for the SMS gateway."""
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from threading import Lock, Thread
from modem_handler import ModemHandler
from auth import AuthManager, require_auth
from config import Config
import logging
import json
import time

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
    
@app.route('/parsed-sms', methods=['POST'])
def handle_parsed_sms():
    """Handle parsed SMS data from the Flutter app."""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Extract and validate fields
        required_fields = ['amount', 'sender', 'phone', 'date', 'balance', 'reference']
        if not all(field in data for field in required_fields):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        # Emit parsed SMS data to the frontend
        socketio.emit('parsed_sms', data, namespace='/')

        return jsonify({'status': 'success', 'message': 'Parsed SMS processed successfully'}), 200
    except Exception as e:
        logger.error("Error handling parsed SMS: %s", str(e), exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

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