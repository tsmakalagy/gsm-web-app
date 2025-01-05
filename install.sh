#!/bin/bash

# Exit on error
set -e

echo "Installing build dependencies..."
sudo apt-get update
sudo apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev curl libbz2-dev

# Download and compile Python 2.7
echo "Downloading Python 2.7.18..."
curl -O https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz
tar -xf Python-2.7.18.tgz
cd Python-2.7.18

echo "Configuring Python 2.7..."
./configure --enable-optimizations

echo "Building Python 2.7..."
make -j$(nproc)

echo "Installing Python 2.7..."
sudo make altinstall

cd ..
rm -rf Python-2.7.18*

# Create application directory
sudo mkdir -p /opt/sms_gateway
sudo chown $USER:$USER /opt/sms_gateway

# Create log directory
sudo mkdir -p /var/log/sms_gateway
sudo chown $USER:$USER /var/log/sms_gateway

# Create run directory
sudo mkdir -p /var/run/sms_gateway
sudo chown $USER:$USER /var/run/sms_gateway

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