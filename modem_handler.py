from gsmmodem.modem import GsmModem
import logging

# Configuration
PORT = '/dev/ttyUSB2'  # Replace with your modem's port
BAUDRATE = 115200      # Replace with your modem's baud rate
PIN = None             # Replace with your SIM PIN if required

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ModemHandler:
    def __init__(self, port, baudrate, pin=None):
        self.port = port
        self.baudrate = baudrate
        self.pin = pin
        self.modem = None

    def connect(self):
        """Connect to the GSM modem."""
        self.modem = GsmModem(self.port, self.baudrate, smsReceivedCallbackFunc=self.on_sms_received_callback)
        self.modem.connect(self.pin)
        logger.info("Modem connected successfully and ready to receive SMS.")
        self.modem.processStoredSms(True)  # Process any stored SMS

    def on_sms_received_callback(self, sms):
        """Callback for received SMS."""
        logger.info("SMS received from {}: {}".format(sms.number, sms.text))
        if self.on_sms_received:
            self.on_sms_received(sms.number, sms.text)

    def send_sms(self, number, message):
        """Send an SMS to a specific number."""
        try:
            self.modem.sendSms(number, message)
            logger.info("SMS sent to {}: {}".format(number, message))
        except Exception as e:
            logger.error("Failed to send SMS: {}".format(e))
            raise

    def send_ussd(self, ussd_code):
        """Send a USSD command and return the response."""
        try:
            logger.info("Sending USSD: {}".format(ussd_code))
            response = self.modem.sendUssd(ussd_code)
            logger.info("USSD Response: {}".format(response.message))
            return response.message
        except Exception as e:
            logger.error("Failed to send USSD: {}".format(e))
            raise

    def close(self):
        """Close the modem connection."""
        if self.modem:
            self.modem.close()
            logger.info("Modem connection closed.")

# Example usage
if __name__ == '__main__':
    handler = ModemHandler(PORT, BAUDRATE, PIN)
    try:
        handler.connect()
        
        # Test sending SMS
        handler.send_sms('+261346449569', 'Hello, this is a test SMS!')

        # Test sending USSD
        ussd_response = handler.send_ussd('#120#')
        print("USSD Response:", ussd_response)

    except Exception as e:
        logger.error("An error occurred: {}".format(e))

    finally:
        handler.close()
