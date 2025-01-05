# config.py
"""Configuration settings for the SMS gateway application."""
import os
import logging
from typing import Optional

class Config:
    # Flask settings
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-please-change-this')
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'  # Set to True for debugging
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '5000'))

    # Modem settings
    MODEM_PORT: str = os.getenv('MODEM_PORT', '/dev/ttyUSB2')
    MODEM_BAUDRATE: int = int(os.getenv('MODEM_BAUDRATE', '115200'))
    MODEM_PIN: Optional[str] = os.getenv('MODEM_PIN', None)
    DEFAULT_USSD_STRING: str = os.getenv('DEFAULT_USSD_STRING', '#357#')

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'DEBUG')  # Set to DEBUG for more information
    LOG_FORMAT: str = '[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s'
    LOG_DIR: str = os.getenv('LOG_DIR', '/var/log/sms_gateway')

    # Server settings
    SERVER_URL: str = os.getenv('SERVER_URL', "http://localhost:5000/sms")
    SOCKET_RETRY_INTERVAL: int = int(os.getenv('SOCKET_RETRY_INTERVAL', '3'))
    SMS_PROCESS_INTERVAL: int = int(os.getenv('SMS_PROCESS_INTERVAL', '10'))

    @classmethod
    def init_logging(cls) -> None:
        """Initialize logging configuration."""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format=cls.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(os.path.join(cls.LOG_DIR, 'app.log'))
            ]
        )
        
        # Set specific loggers to DEBUG
        logging.getLogger('gsmmodem.modem').setLevel(logging.DEBUG)
        logging.getLogger('gsmmodem.serial_comms').setLevel(logging.DEBUG)
        logging.getLogger('modem_handler').setLevel(logging.DEBUG)