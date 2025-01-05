import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'eventlet'  # Required for SocketIO
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/sms_gateway/gunicorn_access.log"
errorlog = "/var/log/sms_gateway/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "sms_gateway"

# Server mechanics
daemon = False
pidfile = "/var/run/sms_gateway/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Server hooks
def on_starting(server):
    """
    Server hook that runs before the master process is initialized.
    """
    # Create necessary directories
    os.makedirs("/var/run/sms_gateway", exist_ok=True)
    os.makedirs("/var/log/sms_gateway", exist_ok=True)

def worker_abort(worker):
    """
    Server hook that runs when a worker receives SIGABRT.
    """
    worker.log.info("Worker received SIGABRT")