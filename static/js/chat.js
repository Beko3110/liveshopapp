// Import shared socket instance
import socket from './socket-client.js';

const chatMessages = document.getElementById('chat-messages');
const messageForm = document.getElementById('message-form');
const ROOM_ID = document.getElementById('stream-container').dataset.roomId;

// Send chat message
messageForm.addEventListener('submit', e => {
    e.preventDefault();
    const input = messageForm.querySelector('input');
    const message = input.value.trim();
    
    if (message) {
        socket.emit('chat_message', {
            message: message,
            room: ROOM_ID
        });
        input.value = '';
    }
});

// Receive chat message
socket.on('chat_message', data => {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message';
    messageDiv.textContent = `${data.username}: ${data.message}`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

// Join room
socket.emit('join_room', {
    room: ROOM_ID
});
