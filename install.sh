#!/bin/bash

# Exit on error
set -e

# Create application directory
sudo mkdir -p /opt/sms_gateway
sudo chown www-data:www-data /opt/sms_gateway

# Create log directory
sudo mkdir -p /var/log/sms_gateway
sudo chown www-data:www-data /var/log/sms_gateway

# Create run directory
sudo mkdir -p /var/run/sms_gateway
sudo chown www-data:www-data /var/run/sms_gateway

# Set up Python virtual environment
python3 -m venv /opt/sms_gateway/venv
source /opt/sms_gateway/venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Copy application files
sudo cp -r * /opt/sms_gateway/
sudo chown -R www-data:www-data /opt/sms_gateway

# Install systemd service
sudo cp sms_gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sms_gateway
sudo systemctl start sms_gateway

echo "Installation completed successfully!"