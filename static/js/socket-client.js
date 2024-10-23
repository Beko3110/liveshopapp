// Socket.io client initialization
const socket = io();

// Export the socket instance and room ID
const ROOM_ID = document.getElementById('stream-container')?.dataset.roomId;

export { socket as default, ROOM_ID };
