# SMS Gateway Service

A Python-based SMS Gateway service that runs on a Raspberry Pi, providing SMS sending capabilities through a REST API. The service is containerized using Docker and accessible through FRP for remote access.

## Features

- Send SMS messages via REST API
- Execute USSD commands (e.g., check balance)
- GSM Modem support
- Docker containerization
- FRP tunneling for remote access
- Health monitoring endpoints

## Prerequisites

- Raspberry Pi
- USB GSM Modem (tested with Huawei E3531)
- Docker and Docker Compose
- Python 2.7
- FRP Server access

## Hardware Setup

1. Connect your GSM modem to the Raspberry Pi USB port
2. Make sure the modem is recognized:
```bash
ls /dev/ttyUSB*
```
3. Insert a SIM card with SMS capabilities

## Project Structure
```
sms-gateway/
├── app/
│   ├── __init__.py      # Application factory and modem initialization
│   ├── config.py        # Configuration settings
│   ├── modem_handler.py # GSM modem handling class
│   └── routes.py        # API endpoints
├── logs/                # Log directory
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env                 # Environment variables
├── .gitignore
├── app.py              # Application entry point
├── requirements.txt     # Python dependencies
├── wsgi.py             # WSGI entry point
└── README.md           # Project documentation
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gsm-web-app.git sms-gateway
cd sms-gateway
```

2. Create and configure environment file:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Build and start the service:
```bash
docker compose up -d
```

## API Endpoints

### 1. Send SMS
```bash
POST /send-sms
Content-Type: application/json

{
    "number": "+261340000000",
    "message": "Your OTP is: 123456"
}

Response:
{
    "status": "success",
    "message": "SMS sent successfully"
}
```

### 2. Execute USSD Command (e.g., Check Balance)
```bash
POST /check-balance
Content-Type: application/json

{
    "ussd_code": "#357#"
}

Response:
{
    "status": "success",
    "ussd_code": "#357#",
    "response": "Your balance is ...",
    "timestamp": "2025-01-15T12:34:56.789Z"
}
```

### 3. Health Check
```bash
GET /health

Response:
{
    "status": "healthy",
    "message": "Connected to Network (Signal: 85)",
    "timestamp": "2025-01-15T12:34:56.789Z"
}
```

## Configuration

### Environment Variables
```env
# Flask Settings
SECRET_KEY=your-secure-secret-key
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Modem Settings
MODEM_PORT=/dev/ttyUSB2
MODEM_BAUDRATE=115200
MODEM_PIN=

# USSD Settings
DEFAULT_USSD_CODE=#357#

# Log Settings
LOG_LEVEL=INFO
```

### FRP Configuration
Located at `/etc/frp/frpc.ini`:
```ini
[common]
server_addr = <server_ip_address>
server_port = 7000
token = your_token
log_file = /var/log/frpc.log
log_level = info

[sms-gateway]
type = http
local_ip = 127.0.0.1
local_port = 5001
remote_port = 5001
custom_domains = <custom_domains>

[pi-ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6001
```

## Docker Commands

Build the container:
```bash
docker compose build
```

Start the service:
```bash
docker compose up -d
```

View logs:
```bash
docker compose logs -f
```

## Troubleshooting

1. Modem Connection Issues:
   - Check if modem is properly connected
   - Verify correct port in configuration
   - Check modem permissions
   - Verify SIM card is properly inserted

2. SMS Sending Failed:
   - Verify SIM card balance
   - Check network signal strength
   - Validate phone number format

3. USSD Command Failed:
   - Check if carrier supports the USSD code
   - Verify network connectivity
   - Check modem USSD compatibility

4. FRP Connection Issues:
   - Check FRP server status
   - Verify network connectivity
   - Check FRP logs: `journalctl -u frpc`

## Monitoring

Check service status:
```bash
# Docker container
docker compose ps

# FRP client
systemctl status frpc
```

View logs:
```bash
# SMS Gateway logs
docker compose logs -f

# FRP logs
journalctl -u frpc -f
```

## Security Considerations

1. API Access
   - Use HTTPS for production
   - Implement API authentication if needed
   - Rate limit requests
   - Validate input data

2. Server Access
   - Secure FRP token
   - Use strong SSH keys
   - Keep system updated
   - Monitor logs for unusual activity

## Support

For issues and support:
1. Check the troubleshooting guide
2. Review container logs
3. Open a GitHub issue

## License

This project is licensed under the MIT License - see the LICENSE file for details.