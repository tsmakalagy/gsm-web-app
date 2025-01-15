import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-please-change-this')
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', '5000'))

    # Modem settings
    MODEM_PORT = os.getenv('MODEM_PORT', '/dev/ttyUSB2')
    MODEM_BAUDRATE = int(os.getenv('MODEM_BAUDRATE', '115200'))
    MODEM_PIN = os.getenv('MODEM_PIN', None)

    # USSD settings
    DEFAULT_USSD_CODE = os.getenv('DEFAULT_USSD_CODE', '#357#')

    # Log settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')