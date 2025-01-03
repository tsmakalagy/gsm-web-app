#!/usr/bin/env python

"""
Demo: handle incoming SMS messages by replying to them

This script listens for incoming SMS messages, displays the sender's number
and the messages, and sends the SMS data to a Flask server.
"""

from __future__ import print_function
from socketIO_client import SocketIO, BaseNamespace
from threading import Thread, Lock
from datetime import date, datetime
from gsmmodem.exceptions import TimeoutException
import requests
import json
import sys
import time

import logging
logging.getLogger('requests').setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING)

# Configuration
async_mode = 'threading'
thread = None
thread_lock = Lock()
INTERVAL = 10
PORT = '/dev/ttyUSB2'
BAUDRATE = 115200
PIN = None  # SIM card PIN (if required)
USSD_STRING = '#357#'
SERVER_URL = "http://localhost:5000/sms"  # Update to match your Flask server URL

from gsmmodem.modem import GsmModem

# Globals
g_modem = None
g_action = "0"
g_ussd_string = '#357#'


def json_serial(obj):
    """JSON serializer for objects not serializable by default JSON code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type {} not serializable".format(type(obj)))


def handleSms(sms):
    """Callback for handling incoming SMS messages."""
    print("== SMS message received ==")
    print("From: {}".format(sms.number))
    print("Time: {}".format(sms.time))
    print("Message:\n{}\n".format(sms.text))
    
    # Convert the datetime object to an ISO 8601 string
    formatted_time = sms.time.isoformat()
    data = {"number": sms.number, "time": formatted_time, "text": sms.text}

    # Emit SMS data to the WebSocket namespace
    handle_namespace.emit('sms_web', json.dumps(data))

    # Send SMS data to the Flask server
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(SERVER_URL, json=data, headers=headers)
        response_data = response.json()
        print("Server response: {}".format(response_data))
    except Exception as e:
        print("Failed to send SMS data to server: {}".format(e))


# Initialize the modem with SMS handling callback
g_modem = GsmModem(PORT, BAUDRATE, smsReceivedCallbackFunc=handleSms)


def readSms():
    """Process stored SMS messages."""
    global g_modem
    g_modem.connect(PIN)
    g_modem.processStoredSms(True)
    g_modem.close()


def sendUSSD(ussd_string):
    """Send a USSD command and handle the response."""
    global g_modem
    g_modem.connect(PIN)
    print("Sending USSD string: {}".format(ussd_string))
    try:
        response = g_modem.sendUssd(ussd_string)
        data = {"text": response.message}
        handle_namespace.emit('ussd', json.dumps(data, default=json_serial))
        print("USSD reply received: {}".format(response.message))
        if response.sessionActive:
            print("Closing USSD session.")
            response.cancel()
    except TimeoutException:
        print("USSD Timeout.")
    except Exception as e:
        print("Unexpected error: {}".format(e))
    finally:
        g_modem.close()


def func_caller(condition):
    """Call appropriate function based on action."""
    if condition == 'S':
        sendUSSD(g_ussd_string)
    elif condition == 'R':
        print("Waiting for SMS....")
        readSms()


def background_thread():
    """Background thread for USSD and SMS processing."""
    while True:
        func_caller(g_action)
        time.sleep(3)


class HandleNamespace(BaseNamespace):
    """WebSocket namespace for handling events."""

    def on_connect(self):
        print("[Connected-client]")
        global thread
        if thread is None:
            thread = Thread(target=background_thread)
            thread.daemon = True
            thread.start()

    def on_start_response(self, *args):
        print("on_start_response", args[0]['action'])
        global g_action
        g_action = args[0]['action']

    def on_sms_response(self, *args):
        print("on_sms_response", args[0]['message'])

    def on_message_event(self, *args):
        global g_action, g_ussd_string
        g_ussd_string = args[0]['code']
        g_action = args[0]['action']


def main():
    global socketIO, handle_namespace
    socketIO = SocketIO('localhost', 5000)  # Use localhost for the Flask server
    handle_namespace = socketIO.define(HandleNamespace, '/handle')
    handle_namespace.emit('start', 'Started')
    socketIO.wait()


if __name__ == '__main__':
    main()