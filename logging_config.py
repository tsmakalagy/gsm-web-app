import os
import logging
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
def ensure_log_directory(log_dir):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

def setup_logging(app, log_dir='/var/log/sms_gateway'):
    ensure_log_directory(log_dir)
    
    # Main application logger
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    app_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    app.logger.addHandler(app_handler)
    app.logger.setLevel(logging.INFO)

    # Error logger
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s [in %(pathname)s:%(lineno)d]:\n%(message)s'
    ))
    error_handler.setLevel(logging.ERROR)
    app.logger.addHandler(error_handler)

    # Modem logger
    modem_logger = logging.getLogger('modem_handler')
    modem_handler = RotatingFileHandler(
        os.path.join(log_dir, 'modem.log'),
        maxBytes=10485760,
        backupCount=5
    )
    modem_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s'
    ))
    modem_logger.addHandler(modem_handler)
    modem_logger.setLevel(logging.INFO)

    # Auth logger
    auth_logger = logging.getLogger('auth')
    auth_handler = RotatingFileHandler(
        os.path.join(log_dir, 'auth.log'),
        maxBytes=10485760,
        backupCount=5
    )
    auth_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s'
    ))
    auth_logger.addHandler(auth_handler)
    auth_logger.setLevel(logging.INFO)

    return app