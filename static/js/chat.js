// Import shared socket instance and ROOM_ID
import socket, { ROOM_ID } from './socket-client.js';

// Initialize chat functionality
function initializeChat() {
    const chatMessages = document.getElementById('chat-messages');
    const messageForm = document.getElementById('message-form');
    
    if (!chatMessages || !messageForm || !ROOM_ID) return;

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
    socket.emit('join_room', { room: ROOM_ID });
}

// Initialize chat when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeChat);

export default initializeChat;
