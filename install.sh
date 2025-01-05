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

# Create conda environment with Python 2.7
echo "Creating conda environment with Python 2.7..."
conda create -n sms_gateway python=2.7 pip -y

# Activate conda environment
echo "Activating conda environment..."
source activate sms_gateway

# Update pip in conda environment
echo "Updating pip..."
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
python get-pip.py --force-reinstall
rm get-pip.py

# Install required packages from requirements.txt
echo "Installing required packages..."
pip install --no-cache-dir -r requirements.txt

# Clone and install gsmmodem
echo "Installing python-gsmmodem..."
git clone https://github.com/faucamp/python-gsmmodem.git
cd python-gsmmodem
pip install .
cd ..
rm -rf python-gsmmodem

# Copy application files
sudo cp -r * /opt/sms_gateway/
sudo chown -R $USER:$USER /opt/sms_gateway

# Create a script to activate conda env and run the service
cat > /opt/sms_gateway/start_service.sh << 'EOL'
#!/bin/bash
source $HOME/miniforge3/etc/profile.d/conda.sh
conda activate sms_gateway
cd /opt/sms_gateway
exec gunicorn --config gunicorn_config.py wsgi:app
EOL

chmod +x /opt/sms_gateway/start_service.sh

# Create systemd service file that uses conda
cat > sms_gateway.service << EOL
[Unit]
Description=SMS Gateway Service
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/sms_gateway
ExecStart=/opt/sms_gateway/start_service.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

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