# gunicorn_config.py
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1  # For WebSocket support, we should use only 1 worker
worker_class = 'sync'  # Changed from 'eventlet' to 'sync'
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

def on_starting(server):
    """
    Server hook that runs before the master process is initialized.
    """
    os.makedirs("/var/run/sms_gateway", exist_ok=True)
    os.makedirs("/var/log/sms_gateway", exist_ok=True)