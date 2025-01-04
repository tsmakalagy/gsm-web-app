# modem_handler.py
"""GSM modem handling module."""
from __future__ import print_function
from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import TimeoutException
from datetime import datetime
import logging
import json
import requests

logger = logging.getLogger(__name__)

class ModemHandler:
    # def __init__(self, config, socketio=None):
    #     """Initialize the modem handler with configuration."""
    #     self.config = config
    #     self.modem = None
    #     self.socketio = socketio
    def __init__(self, config, socketio, sms_callback=None):
        """Initialize the modem handler with configuration."""
        self.config = config
        self.modem = None
        self.socketio = socketio
        self.external_sms_callback = sms_callback

    def connect(self):
        """Connect to the GSM modem."""
        try:
            self.modem = GsmModem(
                self.config.MODEM_PORT,
                self.config.MODEM_BAUDRATE,
                smsReceivedCallbackFunc=self.handle_sms
            )
            self.modem.connect(self.config.MODEM_PIN)
            logger.info("Modem connected successfully")
            return True
        except Exception as e:
            logger.error("Failed to connect to modem: %s", str(e))
            return False

    def disconnect(self):
        """Safely disconnect from the modem."""
        if self.modem:
            try:
                self.modem.close()
                logger.info("Modem disconnected")
            except Exception as e:
                logger.error("Error disconnecting modem: %s", str(e))

    def send_sms(self, number, message):
        """Send an SMS message."""
        if not self.modem:
            raise RuntimeError("Modem not connected")
        
        try:
            self.modem.sendSms(number, message)
            logger.info("SMS sent to %s: %s", number, message)
            return True
        except Exception as e:
            logger.error("Failed to send SMS: %s", str(e))
            raise

    # def handle_sms(self, sms):
    #     """Callback for handling incoming SMS messages."""
    #     try:
    #         logger.info("=== SMS message received ===")
    #         logger.info("From: %s", sms.number)
    #         logger.info("Time: %s", sms.time)
    #         logger.info("Message: %s", sms.text)
            
    #         # Prepare data for WebSocket
    #         data = {
    #             "number": sms.number,
    #             "time": sms.time.isoformat() if hasattr(sms.time, 'isoformat') else str(sms.time),
    #             "text": sms.text
    #         }
            
    #         # Emit to WebSocket if available
    #         if self.socketio:
    #             logger.info("Emitting SMS data through WebSocket")
    #             try:
    #                 self.socketio.emit('sms_grab', data, namespace='/',
    #                      broadcast=True)
    #                 logger.info("SMS data emitted successfully")
    #             except Exception as e:
    #                 logger.error("Error emitting SMS: %s", str(e))
            
    #         return data
            
    #     except Exception as e:
    #         logger.error("Error handling SMS: %s", str(e))
    #         return None
    def handle_sms(self, sms):
        """Callback for handling incoming SMS messages."""
        try:
            logger.info("=== SMS message received ===")
            logger.info("From: %s", sms.number)
            logger.info("Time: %s", sms.time)
            logger.info("Message: %s", sms.text)
            
            # Prepare data
            data = {
                "number": sms.number,
                "time": sms.time.isoformat() if hasattr(sms.time, 'isoformat') else str(sms.time),
                "text": sms.text
            }
            
            # Send to app.py REST endpoint
            try:
                response = requests.post('http://localhost:5000/forward_sms', json=data)
                if response.status_code == 200:
                    logger.info("SMS data forwarded successfully")
                else:
                    logger.error("Failed to forward SMS: %s", response.text)
            except Exception as e:
                logger.error("Error forwarding SMS: %s", str(e))
            
            return data

        except Exception as e:
            logger.error("Error handling SMS: %s", str(e))
            return None

    def send_ussd(self, ussd_string):
        """Send a USSD command and get the response."""
        if not self.modem:
            logger.error("Modem not connected when trying to send USSD")
            raise RuntimeError("Modem not connected")

        logger.info("Attempting to send USSD command: %s", ussd_string)
        try:
            response = self.modem.sendUssd(ussd_string)
            logger.info("USSD response received: %s", response.message)
            result = {
                "status": "success",
                "response": response.message
            }
            
            if response.sessionActive:
                logger.info("USSD session active, canceling session")
                response.cancel()
                
            return result
        except TimeoutException:
            logger.error("USSD request timed out for command: %s", ussd_string)
            return {"status": "timeout", "response": "USSD request timed out"}
        except Exception as e:
            logger.error("Error sending USSD command: %s - %s", ussd_string, str(e))
            return {"status": "error", "response": str(e)}

    def process_stored_sms(self):
        """Process any stored SMS messages."""
        if not self.modem:
            raise RuntimeError("Modem not connected")
        
        try:
            self.modem.processStoredSms(True)
        except Exception as e:
            logger.error("Error processing stored SMS: %s", str(e))
            raise