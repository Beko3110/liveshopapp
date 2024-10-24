// Socket.io client initialization
const socket = io();

// Get room ID from stream container if it exists
const streamContainer = document.getElementById('stream-container');
export const ROOM_ID = streamContainer ? streamContainer.dataset.roomId : null;

// Export socket instance as default
export default socket;
