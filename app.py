from flask import Flask, jsonify, request
from modem_handler import ModemHandler

# Configuration
class Config:
    MODEM_PORT = "/dev/ttyUSB2"
    MODEM_BAUDRATE = 115200
    MODEM_PIN = None

app = Flask(__name__)

# Initialize the modem handler
modem_handler = ModemHandler(Config, None)

@app.route('/send-sms', methods=['POST'])
def send_sms():
    data = request.json
    phone_number = data.get('phone_number')
    message = data.get('message')

    if not phone_number or not message:
        return jsonify({"status": "error", "message": "Phone number and message are required"}), 400

    try:
        modem_handler.send_sms(phone_number, message)
        return jsonify({"status": "success", "message": "SMS sent successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/send-ussd', methods=['POST'])
def send_ussd():
    data = request.json
    ussd_code = data.get('ussd_code')

    if not ussd_code:
        return jsonify({"status": "error", "message": "USSD code is required"}), 400

    try:
        response = modem_handler.send_ussd(ussd_code)
        return jsonify({"status": "success", "response": response}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)