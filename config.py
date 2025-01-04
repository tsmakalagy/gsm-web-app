# config.py
"""Configuration settings for the SMS gateway application."""

class Config:
    # Flask settings
    SECRET_KEY = 'your-secret-key-please-change-this'
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = 5000

    # Modem settings
    MODEM_PORT = '/dev/ttyUSB2'
    MODEM_BAUDRATE = 115200
    MODEM_PIN = None
    DEFAULT_USSD_STRING = '#357#'

    # Server settings
    SERVER_URL = "http://localhost:5000/sms"
    SOCKET_RETRY_INTERVAL = 3
    SMS_PROCESS_INTERVAL = 10