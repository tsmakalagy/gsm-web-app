from flask import Flask
from .config import Config
from .modem_handler import ModemHandler
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize ModemHandler
modem_handler = None

def init_modem():
    """Initialize the GSM modem."""
    try:
        handler = ModemHandler(config=Config)
        if handler.connect() and handler.wait_for_network():
            logger.info("Modem initialized successfully")
            return handler
    except Exception as e:
        logger.error("Error initializing modem: %s", str(e))
    return None

# Initialize modem with retries
for attempt in range(3):
    modem_handler = init_modem()
    if modem_handler:
        logger.info("Modem initialized on attempt %d", attempt + 1)
        break
    logger.warning("Modem initialization attempt %d failed", attempt + 1)

if not modem_handler:
    logger.error("Failed to initialize modem after 3 attempts")

# Import routes after app initialization
from app import routes