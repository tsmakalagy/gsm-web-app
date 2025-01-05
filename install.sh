#!/bin/bash

# Exit on error
set -e

# Create application directory
sudo mkdir -p /opt/sms_gateway
sudo chown $USER:$USER /opt/sms_gateway

# Create log directory
sudo mkdir -p /var/log/sms_gateway
sudo chown $USER:$USER /var/log/sms_gateway

# Create run directory
sudo mkdir -p /var/run/sms_gateway
sudo chown $USER:$USER /var/run/sms_gateway

# Install Python 2.7 and required system packages
sudo apt-get update
sudo apt-get install -y python2.7 curl

# Install pip for Python 2.7
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
sudo python2.7 get-pip.py
rm get-pip.py

# Install virtualenv
sudo python2.7 -m pip install virtualenv

# Set up Python 2.7 virtual environment
python2.7 -m virtualenv /opt/sms_gateway/venv
source /opt/sms_gateway/venv/bin/activate

# Install required packages from requirements.txt
pip install -r requirements.txt

# Clone and install gsmmodem
git clone https://github.com/faucamp/python-gsmmodem.git
cd python-gsmmodem
pip install .
cd ..
rm -rf python-gsmmodem

# Copy application files
sudo cp -r * /opt/sms_gateway/
sudo chown -R $USER:$USER /opt/sms_gateway

# Install systemd service
sudo cp sms_gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sms_gateway
sudo systemctl start sms_gateway

# Add current user to dialout group for serial port access
sudo usermod -a -G dialout $USER

# Set proper permissions for USB device
if [ -e /dev/ttyUSB2 ]; then
    sudo chmod 666 /dev/ttyUSB2
fi

echo "Installation completed successfully!"
echo "Note: You may need to log out and back in for the dialout group changes to take effect."