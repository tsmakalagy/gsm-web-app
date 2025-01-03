#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from threading import Lock
from flask import Flask, jsonify, abort, make_response, render_template, session, request
from flask_socketio import SocketIO, Namespace, emit, send
from werkzeug import generate_password_hash, check_password_hash
import time
import iso8601
import json
import sys
import re
from datetime import datetime

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None



app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

_start = "N"  # Default value, can be updated later


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route('/start', methods=['POST'])
def start():
    try:
        if not request.json or not 'action' in request.json or not 'code' in request.json:
            abort(400)

        _action = request.json['action']
        _code = request.json['code']
        if _action :
            socketio.emit('message_event', {'action': _action, 'code': _code}, namespace='/handle') # SEND SOCKET TO handle_sms.py
            return jsonify({'response':'started', 'action':'S'})
        else:
            return jsonify({'response':'Error is encountered'})

    except Exception as e:
        return jsonify({'Exception':str(e)})

@app.route('/sms', methods=['POST'])
def receive_sms():
    global _start  # Ensure the global variable is used
    try:
        if not request.json or not 'number' in request.json or not 'time' in request.json or not 'text' in request.json:
            abort(400)

        _number = request.json['number']
        _text   = request.json['text']
        _time   = request.json['time']

        _data   = "Message received on: " + _time + ", Content: " + _text

        socketio.emit('my_response', {'data': _data}, namespace='/test')

        if _start == "Y":
            return jsonify({'response':'started', 'action':'R'})
        else:
            return jsonify({'response':'Error is encountered'})
    except Exception as e:
        return jsonify({'Exception': str(e)})

@app.route('/set_start', methods=['POST'])
def set_start():
    global _start
    try:
        data = request.json
        _start = data.get('start', "N")  # Default to "N" if not provided
        return jsonify({'response': '_start set to {}'.format(_start)})
    except Exception as e:
        return jsonify({'Exception': str(e)})

@socketio.on('sms_web', namespace='/handle')
def test_message(message):
    #print(message)
    message = json.loads(message)
    _sms_text = message["text"]
    
    socketio.emit('sms_web_response', {'data': _sms_text})

@socketio.on('sms', namespace='/handle')
def test_message(message):
    print(message)
    message = json.loads(message)
    _sms_text = message["text"]
    
    socketio.emit('sms_web_response', {'data': _sms_text})

@socketio.on('ussd', namespace='/handle')
def test_message(message):
    print(message)
    message = json.loads(message)
    _ussd_text = message["text"]
    socketio.emit('ussd_response', {'data': _ussd_text})

@socketio.on('my_event')
def test_handle(message):
    print('Yes baby: {0}'.format(message['data']))
    socketio.emit('message_event', {'action': 'S', 'code': message['data']}, namespace='/handle')

@socketio.on('start', namespace='/handle')
def test_message(message):
    print(message)
    emit('start_response', {'action': 'R'})

@socketio.on('connect')
def test_connect():
    print('Connected [app.py]')

if __name__ == '__main__':
    socketio.run(app, debug=True)
