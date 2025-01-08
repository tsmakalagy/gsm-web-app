# modem_handler.py
"""GSM modem handling module."""
from __future__ import print_function
from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import TimeoutException
from datetime import datetime
import logging
import time

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
        logger.info("ModemHandler initialized with config: PORT=%s, BAUDRATE=%s", 
                   config.MODEM_PORT, config.MODEM_BAUDRATE)

    def check_network_status(self):
        """Check GSM network registration status."""
        try:
            if not self.modem:
                return False, "Modem not connected"

            # Check if registered to network
            network_name = self.modem.networkName
            signal_strength = self.modem.signalStrength
            
            logger.info("Network Status:")
            logger.info(" - Network: %s", network_name)
            logger.info(" - Signal Strength: %s", signal_strength)
            
            if not network_name:
                return False, "Not registered to network"
                
            return True, "Connected to " + network_name
            
        except Exception as e:
            logger.error("Error checking network status: %s", str(e))
            return False, str(e)

    def connect(self):
        """Connect to the GSM modem."""
        try:
            logger.info("Attempting to connect to modem on port %s", self.config.MODEM_PORT)
            
            import os
            if not os.path.exists(self.config.MODEM_PORT):
                logger.error("Modem port %s does not exist!", self.config.MODEM_PORT)
                return False

            self.modem = GsmModem(
                self.config.MODEM_PORT,
                self.config.MODEM_BAUDRATE,
                smsReceivedCallbackFunc=self.handle_sms
            )

            logger.info("Connecting to modem...")
            self.modem.connect(self.config.MODEM_PIN)

            # Wait for network registration
            
            max_wait = 30  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                network_status, message = self.check_network_status()
                if network_status:
                    logger.info("Network registered: %s", message)
                    return True
                    
                logger.info("Waiting for network registration...")
                time.sleep(2)


            logger.info("Modem connected successfully")
            return True
        except Exception as e:
            logger.error("Failed to connect to modem: %s", str(e))
            return False

    def wait_for_network(self, timeout=30):
        """Wait for network registration with timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if self.modem.waitForNetworkCoverage(timeout=5):
                    network_name = self.modem.networkName
                    signal = self.modem.signalStrength
                    logger.info("Network registered: %s (Signal: %s)", network_name, signal)
                    return True
            except Exception as e:
                logger.warning("Error while waiting for network: %s", str(e))
            
            logger.info("Still waiting for network...")
            time.sleep(2)
            
        logger.error("Timeout waiting for network registration")
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
            logger.error("Cannot send SMS: Modem not connected")
            raise RuntimeError("Modem not connected")

        try:
            # Check network status first
            network_ok, status_msg = self.check_network_status()
            if not network_ok:
                logger.error("Cannot send SMS: %s", status_msg)
                raise RuntimeError("Network not available: " + status_msg)

            # Try to send with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info("Sending SMS to %s (attempt %d/%d)", 
                              number, attempt + 1, max_retries)
                    self.modem.sendSms(number, message)
                    logger.info("SMS sent successfully")
                    return True
                except Exception as e:
                    if "CMS 500" in str(e):
                        logger.warning("CMS 500 error, retrying...")
                        time.sleep(2)  # Wait before retry
                        continue
                    raise  # Re-raise if it's a different error
                    
            raise RuntimeError("Failed to send SMS after {0} attempts".format(max_retries))
            
        except Exception as e:
            logger.error("Failed to send SMS: %s", str(e), exc_info=True)
            raise
        
        # try:
        #     self.modem.sendSms(number, message)
        #     logger.info("SMS sent to %s: %s", number, message)
        #     return True
        # except Exception as e:
        #     logger.error("Failed to send SMS: %s", str(e))
        #     raise

    # def handle_sms(self, sms):
    #     """Callback for handling incoming SMS messages."""
    #     try:
    #         logger.info("=== SMS message received ===")
    #         logger.info("From: %s", sms.number)
    #         logger.info("Time: %s", sms.time)
    #         logger.info("Message: %s", sms.text)
            
    #         # Prepare data
    #         data = {
    #             "number": sms.number,
    #             "time": sms.time.isoformat() if hasattr(sms.time, 'isoformat') else str(sms.time),
    #             "text": sms.text
    #         }
            
    #         # Send to app.py REST endpoint
    #         try:
    #             response = requests.post('http://localhost:5000/forward_sms', json=data)
    #             if response.status_code == 200:
    #                 logger.info("SMS data forwarded successfully")
    #             else:
    #                 logger.error("Failed to forward SMS: %s", response.text)
    #         except Exception as e:
    #             logger.error("Error forwarding SMS: %s", str(e))
            
    #         return data

    #     except Exception as e:
    #         logger.error("Error handling SMS: %s", str(e))
    #         return None

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