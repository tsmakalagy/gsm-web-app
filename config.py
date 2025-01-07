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

    SUPABASE_API_URL = "https://jfdpajjqwfpapdakiohz.supabase.co/rest/v1/mobile_money_sms"
    SUPABASE_API_KEY= "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpmZHBhampxd2ZwYXBkYWtpb2h6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzYyNjUxNjQsImV4cCI6MjA1MTg0MTE2NH0.R3LhaKyREcXrBwNj8XsX8AOdgme5b382OZSR1yUFHRk"
