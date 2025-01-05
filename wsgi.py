from app import app, socketio
from logging_config import setup_logging

# Setup logging
app = setup_logging(app)

if __name__ == "__main__":
    socketio.run(app)