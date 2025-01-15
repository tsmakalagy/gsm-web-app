# modem_handler.py
from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import TimeoutException
import logging
import time

logger = logging.getLogger(__name__)

class ModemHandler:
    def __init__(self, config):
        self.config = config
        self.modem = None

    def connect(self):
        """Connect to the GSM modem."""
        try:
            self.modem = GsmModem(
                self.config.MODEM_PORT,
                self.config.MODEM_BAUDRATE
            )
            self.modem.connect(self.config.MODEM_PIN)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to modem: {e}")
            return False

    def check_network_status(self):
        """Check GSM network registration status."""
        try:
            if not self.modem:
                return False, "Modem not connected"

            network_name = self.modem.networkName
            signal_strength = self.modem.signalStrength
            
            if not network_name:
                return False, "Not registered to network"
                
            return True, f"Connected to {network_name} (Signal: {signal_strength})"
            
        except Exception as e:
            logger.error(f"Error checking network status: {e}")
            return False, str(e)

    def wait_for_network(self, timeout=30):
        """Wait for network registration."""
        try:
            return self.modem.waitForNetworkCoverage(timeout)
        except Exception as e:
            logger.error(f"Error waiting for network: {e}")
            return False

    def send_sms(self, number, message):
        """Send an SMS message."""
        if not self.modem:
            raise RuntimeError("Modem not connected")

        try:
            # Verify network status
            network_ok, status_msg = self.check_network_status()
            if not network_ok:
                raise RuntimeError(f"Network not available: {status_msg}")

            # Send with retries
            for attempt in range(3):
                try:
                    self.modem.sendSms(number, message)
                    logger.info(f"SMS sent to {number}")
                    return
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        raise
                    time.sleep(2)  # Wait before retry
                    
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            raise

    def send_ussd(self, ussd_string):
        """Send a USSD command and get the response."""
        if not self.modem:
            raise RuntimeError("Modem not connected")

        logger.info(f"Sending USSD command: {ussd_string}")
        try:
            response = self.modem.sendUssd(ussd_string)
            logger.info(f"USSD response received: {response.message}")
            
            if response.sessionActive:
                logger.info("USSD session active, canceling session")
                response.cancel()
                
            return {
                "status": "success",
                "response": response.message
            }
        except TimeoutException:
            logger.error(f"USSD request timed out: {ussd_string}")
            return {
                "status": "error", 
                "response": "Request timed out"
            }
        except Exception as e:
            logger.error(f"USSD error: {e}")
            return {
                "status": "error", 
                "response": str(e)
            }