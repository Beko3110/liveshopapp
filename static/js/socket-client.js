// Socket.io client initialization
const socket = io();

// Get room ID from stream container if it exists
const ROOM_ID = document.getElementById('stream-container')?.dataset.roomId;

// Export both socket and ROOM_ID
export { socket as default, ROOM_ID };
