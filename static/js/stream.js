// Import shared socket instance and ROOM_ID
import socket, { ROOM_ID } from './socket-client.js';

// WebRTC configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
};

let localStream;
let peerConnection;
const streamContainer = document.getElementById('stream-container');

// Start stream (for sellers)
async function startStream() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        document.getElementById('localVideo').srcObject = localStream;
        
        peerConnection = new RTCPeerConnection(configuration);
        
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
        
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                socket.emit('ice_candidate', { candidate: event.candidate, room: ROOM_ID });
            }
        };
        
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        socket.emit('offer', { offer, room: ROOM_ID });

        // Show stop button after starting stream
        document.getElementById('startStream').style.display = 'none';
        document.getElementById('stopStream').style.display = 'inline-block';
    } catch (error) {
        console.error('Error starting stream:', error);
    }
}

// Stop stream function
function stopStream() {
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        document.getElementById('localVideo').srcObject = null;
    }
    if (peerConnection) {
        peerConnection.close();
    }
    document.getElementById('startStream').style.display = 'inline-block';
    document.getElementById('stopStream').style.display = 'none';
    
    // Notify server that stream has ended
    socket.emit('stream_ended', { room: ROOM_ID });
}

// Join stream (for viewers)
socket.on('offer', async data => {
    try {
        peerConnection = new RTCPeerConnection(configuration);
        
        peerConnection.ontrack = event => {
            document.getElementById('remoteVideo').srcObject = event.streams[0];
        };
        
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                socket.emit('ice_candidate', { candidate: event.candidate, room: ROOM_ID });
            }
        };
        
        await peerConnection.setRemoteDescription(data.offer);
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        
        socket.emit('answer', { answer, room: ROOM_ID });
    } catch (error) {
        console.error('Error joining stream:', error);
    }
});

// Handle ICE candidates
socket.on('ice_candidate', async data => {
    try {
        if (peerConnection) {
            await peerConnection.addIceCandidate(data.candidate);
        }
    } catch (error) {
        console.error('Error adding ICE candidate:', error);
    }
});

// Initialize buttons when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (!streamContainer) return;
    
    const startStreamBtn = document.getElementById('startStream');
    const stopStreamBtn = document.getElementById('stopStream');
    
    if (startStreamBtn) {
        startStreamBtn.addEventListener('click', startStream);
    }
    if (stopStreamBtn) {
        stopStreamBtn.addEventListener('click', stopStream);
    }
    
    // Join room on connection
    socket.emit('join_room', { room: ROOM_ID });
});
