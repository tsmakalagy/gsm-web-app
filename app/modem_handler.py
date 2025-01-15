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
            logger.error("Failed to connect to modem: {}".format(e))
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
                
            return True, "Connected to {} (Signal: {})".format(network_name, signal_strength)
            
        except Exception as e:
            logger.error("Error checking network status: {}".format(e))
            return False, str(e)

    def wait_for_network(self, timeout=30):
        """Wait for network registration."""
        try:
            return self.modem.waitForNetworkCoverage(timeout)
        except Exception as e:
            logger.error("Error waiting for network: {}".format(e))
            return False

    def send_sms(self, number, message):
        """Send an SMS message."""
        if not self.modem:
            raise RuntimeError("Modem not connected")

        try:
            # Verify network status
            network_ok, status_msg = self.check_network_status()
            if not network_ok:
                raise RuntimeError("Network not available: {}".format(status_msg))

            # Send with retries
            for attempt in range(3):
                try:
                    self.modem.sendSms(number, message)
                    logger.info("SMS sent to {}".format(number))
                    return
                except Exception as e:
                    if attempt == 2:  # Last attempt
                        raise
                    time.sleep(2)  # Wait before retry
                    
        except Exception as e:
            logger.error("Failed to send SMS: {}".format(e))
            raise

    def send_ussd(self, ussd_string):
        """Send a USSD command and get the response."""
        if not self.modem:
            raise RuntimeError("Modem not connected")

        logger.info("Sending USSD command: {}".format(ussd_string))
        try:
            response = self.modem.sendUssd(ussd_string)
            logger.info("USSD response received: {}".format(response.message))
            
            if response.sessionActive:
                logger.info("USSD session active, canceling session")
                response.cancel()
                
            return {
                "status": "success",
                "response": response.message
            }
        except TimeoutException:
            logger.error("USSD request timed out: {}".format(ussd_string))
            return {
                "status": "error", 
                "response": "Request timed out"
            }
        except Exception as e:
            logger.error("USSD error: {}".format(e))
            return {
                "status": "error", 
                "response": str(e)
            }