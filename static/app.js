const socket = io('http://localhost:5000');

function sendUssd() {
    const ussdCode = document.getElementById('ussd_code').value;
	console.log("clicked");    
	socket.emit('send_ussd', { ussd_code: ussdCode });
}

function sendSms() {
    const number = document.getElementById('sms_number').value;
    const message = document.getElementById('sms_message').value;
    socket.emit('send_sms', { number: number, message: message });
}

socket.on('ussd_response', (data) => {
    const responseElem = document.getElementById('ussd_response');
    responseElem.textContent = `Response: ${data.response}`;
    responseElem.classList.add('text-success');
});

socket.on('sms_status', (data) => {
    const statusElem = document.getElementById('sms_status');
    statusElem.textContent = data.status;
    statusElem.classList.add('text-success');
});

socket.on('incoming_sms', (data) => {
    const smsList = document.getElementById('incoming_sms');
    const smsItem = document.createElement('li');
    smsItem.className = 'list-group-item';
    smsItem.textContent = `From ${data.number}: ${data.message}`;
    smsList.appendChild(smsItem);
});

socket.on('error', (data) => {
    alert(`Error: ${data.message}`);
});

socket.on('connect', () => {
    console.log('WebSocket connected');
});

socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
});

socket.on('connect_error', (error) => {
    console.error('WebSocket connection error:', error);
});
