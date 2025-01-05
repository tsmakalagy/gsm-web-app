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
from typing import Optional, Dict, Any

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
thread: Optional[Thread] = None
thread_lock = Lock()
modem_handler: Optional[ModemHandler] = None

def handle_sms_callback(sms: Dict[str, Any]) -> None:
    """Handle incoming SMS messages."""
    logger.info("SMS received from: %s", sms['number'])
    
    try:
        data = {
            "number": str(sms['number']),
            "time": sms['time'].isoformat() if hasattr(sms['time'], 'isoformat') else str(sms['time']),
            "text": str(sms['text'])
        }
        
        socketio.emit('sms_web', json.dumps(data), namespace='/')
        logger.info("SMS data emitted to websocket")
    except Exception as e:
        logger.error(f"Error in handle_sms_callback: {str(e)}", exc_info=True)

def initialize_modem() -> Optional[ModemHandler]:
    """Initialize and connect to the GSM modem."""
    try:
        logger.info("Initializing modem...")
        handler = ModemHandler(
            config=Config,
            socketio=socketio,
            sms_callback=handle_sms_callback
        )
        
        if not handler.connect():
            logger.error("Failed to connect to modem")
            return None
            
        if not handler.wait_for_network():
            logger.error("Failed to register with network")
            return None
            
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

auth_manager = AuthManager(modem_handler, Config.SECRET_KEY)

@app.route('/')
def index():
    """Serve the frontend interface."""
    return render_template('index.html')

@app.route('/send_sms', methods=['POST'])
def send_sms():
    """API endpoint to send SMS messages."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400

        number = data.get('number')
        message = data.get('message')

        if not number or not message:
            return jsonify({
                'status': 'error',
                'message': 'Phone number and message are required.'
            }), 400

        if not modem_handler:
            return jsonify({
                'status': 'error',
                'message': 'SMS service unavailable'
            }), 503

        modem_handler.send_sms(str(number), str(message))
        return jsonify({
            'status': 'success',
            'message': 'SMS sent successfully'
        })

    except Exception as e:
        logger.error("Failed to send SMS: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/send_ussd', methods=['POST'])
def send_ussd():
    """API endpoint to send USSD commands."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400

        ussd_code = data.get('ussd_code')
        if not ussd_code:
            logger.error("USSD code missing in request")
            return jsonify({
                'status': 'error',
                'message': 'USSD code is required.'
            }), 400

        if not modem_handler:
            return jsonify({
                'status': 'error',
                'message': 'USSD service unavailable'
            }), 503

        logger.info("Received USSD request with code: %s", ussd_code)
        response = modem_handler.send_ussd(str(ussd_code))
        
        logger.info("USSD response: %s", response)
        try:
            socketio.emit('ussd_response', 
                         {'response': response.get('response')},
                         namespace='/')
            logger.info("USSD response emitted successfully")
        except Exception as e:
            logger.error(f"Failed to emit USSD response: {str(e)}")
        
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
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400

        socketio.emit('sms_grab', data, namespace='/')
        return jsonify({'status': 'SMS forwarded successfully'})
    except Exception as e:
        logger.error("Error forwarding SMS: %s", str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/auth/send-code', methods=['POST'])
def send_verification():
    """Send verification code to phone number."""
    logger.info("=== New verification code request ===")
    
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data in request")
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400
        
        phone_number = data.get('phone_number')
        logger.info("Extracted phone number: %s", phone_number)
        
        if not phone_number:
            logger.warning("Missing phone number in request data")
            return jsonify({
                'status': 'error',
                'message': 'Phone number is required'
            }), 400
        
        if not auth_manager:
            logger.error("auth_manager is None")
            return jsonify({
                'status': 'error',
                'message': 'Authentication service not available'
            }), 503
            
        logger.info("Calling auth_manager.send_verification_code...")
        result = auth_manager.send_verification_code(str(phone_number))
        logger.info("Result from send_verification_code: %s", result)
        
        if result.get('status') == 'error':
            logger.error("Error from send_verification_code: %s", 
                        result.get('message'))
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error in send_verification: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/auth/verify-code', methods=['POST'])
def verify_code():
    """Verify the code sent to phone number."""
    logger.info("Received code verification request")
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data provided'
            }), 400

        phone_number = data.get('phone_number')
        code = data.get('code')
        
        if not phone_number or not code:
            logger.warning("Missing phone number or code in request")
            return jsonify({
                'status': 'error',
                'message': 'Phone number and code are required'
            }), 400
            
        logger.info("Verifying code for %s", phone_number)
        result = auth_manager.verify_code(str(phone_number), str(code))
        logger.info("Verification result: %s", result)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error("Error verifying code: %s", str(e), exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/protected-resource')
@require_auth(auth_manager)
def protected_resource():
    """Example of a protected endpoint."""
    logger.info("Protected resource accessed by %s", request.user_phone)
    return jsonify({
        'message': f"Hello {request.user_phone}! This is a protected resource."
    })

def background_worker():
    """Background worker to maintain modem connection and process stored SMS."""
    while True:
        try:
            if modem_handler and not modem_handler.modem:
                modem_handler.connect()
            if modem_handler:
                modem_handler.process_stored_sms()
        except Exception as e:
            logger.error("Background worker error: %s", str(e), exc_info=True)
            if modem_handler:
                try:
                    modem_handler.disconnect()
                except Exception as disconnect_error:
                    logger.error("Error disconnecting modem: %s", str(disconnect_error))
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