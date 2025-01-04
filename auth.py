# auth.py
"""Authentication module for SMS gateway."""
from flask import jsonify, request
import jwt
import random
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, modem_handler, secret_key, code_ttl=300):
        """
        Initialize Auth Manager.
        
        Args:
            modem_handler: ModemHandler instance for sending SMS
            secret_key: Secret key for JWT tokens
            code_ttl: Time-to-live for verification codes in seconds (default 5 minutes)
        """
        self.modem_handler = modem_handler
        self.secret_key = secret_key
        self.code_ttl = code_ttl
        self._verification_codes = {}  # Store codes in memory

        # Log initial state
        logger.info("AuthManager initialized with:")
        logger.info(" - Code TTL: %d seconds", code_ttl)
        logger.info(" - Modem Handler: %s", "Present" if modem_handler else "Missing")
        
    def generate_verification_code(self):
        """Generate a 6-digit verification code."""
        code = ''.join(random.choice('0123456789') for _ in range(6))
        logger.debug("Generated verification code: %s", code)
        return code
    
    def send_verification_code(self, phone_number):
        """Send verification code via SMS."""
        logger.info("Starting send_verification_code for number: %s", phone_number)
        try:
            # Check modem handler
            if not self.modem_handler:
                logger.error("Modem handler is None")
                return {
                    'status': 'error',
                    'message': 'SMS service unavailable - no modem handler'
                }
            
            # Generate code
            logger.debug("Generating verification code...")
            code = self.generate_verification_code()
            expiry = time.time() + self.code_ttl
            logger.debug("Code will expire at: %s", 
                        time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry)))
            
            # Store code
            logger.debug("Storing code in memory...")
            self._verification_codes[phone_number] = {
                'code': code,
                'expiry': expiry
            }
            logger.debug("Current stored codes: %s", 
                        list(self._verification_codes.keys()))
            
            # Prepare message
            message = "Your code: {0}".format(code)
            logger.debug("Prepared SMS message: %s", message)
            
            # Send SMS
            logger.info("Attempting to send SMS via modem_handler...")
            
            try:
                self.modem_handler.send_sms(phone_number, message)
                logger.info("SMS sent successfully")
            except Exception as sms_error:
                logger.error("SMS sending failed: %s", str(sms_error), exc_info=True)
                raise Exception("Failed to send SMS: " + str(sms_error))
            
            logger.info("Verification code sent successfully")
            return {
                'status': 'success',
                'message': 'Verification code sent',
                'expires_in': self.code_ttl
            }
            
        except Exception as e:
            logger.error("Error in send_verification_code: %s", str(e), exc_info=True)
            # Log detailed state
            logger.error("Current state:")
            logger.error(" - Modem handler: %s", type(self.modem_handler))
            logger.error(" - Number of stored codes: %d", 
                        len(self._verification_codes))
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def verify_code(self, phone_number, code):
        """Verify the provided code for the phone number."""
        stored = self._verification_codes.get(phone_number)
        
        if not stored:
            return {
                'status': 'error',
                'message': 'Code not found'
            }
            
        if time.time() > stored['expiry']:
            self._verification_codes.pop(phone_number)
            return {
                'status': 'error',
                'message': 'Code expired'
            }
            
        if stored['code'] != code:
            return {
                'status': 'error',
                'message': 'Invalid code'
            }
            
        # Code is valid - remove it and generate JWT
        self._verification_codes.pop(phone_number)
        
        token = jwt.encode(
            {
                'phone': phone_number,
                'exp': int(time.time()) + (24 * 60 * 60)  # 24 hour expiry
            },
            self.secret_key,
            algorithm='HS256'
        )
        
        return {
            'status': 'success',
            'token': token,
            'message': 'Phone number verified successfully'
        }

def require_auth(auth_manager):
    """Decorator to protect API endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(" ")[1]
                except IndexError:
                    return jsonify({'message': 'Token is missing'}), 401

            if not token:
                return jsonify({'message': 'Token is missing'}), 401

            try:
                data = jwt.decode(
                    token, 
                    auth_manager.secret_key,
                    algorithms=['HS256']
                )
                request.user_phone = data['phone']
            except Exception as e:
                return jsonify({
                    'message': 'Token is invalid: {0}'.format(str(e))
                }), 401

            return f(*args, **kwargs)

        return decorated
    return decorator