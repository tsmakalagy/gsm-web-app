# app/routes.py
from flask import jsonify, request
from app import app, modem_handler
import logging

logger = logging.getLogger(__name__)

@app.route('/health')
def health():
    """Health check endpoint."""
    if not modem_handler:
        return jsonify({
            'status': 'error',
            'message': 'Modem not initialized'
        }), 503

    network_ok, message = modem_handler.check_network_status()
    return jsonify({
        'status': 'healthy' if network_ok else 'error',
        'message': message
    })

@app.route('/send-sms', methods=['POST'])
def send_sms():
    """Send SMS endpoint."""
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        number = data.get('number')
        message = data.get('message')

        if not number or not message:
            return jsonify({
                'status': 'error',
                'message': 'Phone number and message are required'
            }), 400

        # Send SMS
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
    
@app.route('/check-balance', methods=['POST'])
def check_balance():
    """Check balance using USSD code."""
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        ussd_code = data.get('ussd_code', app.config['DEFAULT_USSD_CODE'])
        
        logger.info("Sending USSD code: %s", ussd_code)
        response = modem_handler.send_ussd(ussd_code)
        
        return jsonify({
            'status': 'success',
            'ussd_code': ussd_code,
            'response': response.get('response'),
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error("Failed to execute USSD command: %s", str(e))
        return jsonify({
            'status': 'error',
            'message': str(e),
            'ussd_code': ussd_code
        }), 500