from app import app, socketio
from logging_config import setup_logging

# Setup logging
app = setup_logging(app)

if __name__ == "wsgi":
    # This allows us to use the SocketIO with Gunicorn
    app = socketio.WSGIApp(socketio, app)