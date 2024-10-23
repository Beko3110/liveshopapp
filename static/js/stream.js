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

// Show error message function
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger';
    errorDiv.textContent = message;
    document.getElementById('stream-container').prepend(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
}

// Start stream (for sellers)
async function startStream() {
    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Media devices not supported in your browser');
        }
        
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        const localVideo = document.getElementById('localVideo');
        if (!localVideo) {
            throw new Error('Local video element not found');
        }
        localVideo.srcObject = localStream;
        
        peerConnection = new RTCPeerConnection(configuration);
        
        localStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, localStream);
        });
        
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                socket.emit('ice_candidate', { candidate: event.candidate, room: ROOM_ID });
            }
        };

        peerConnection.onconnectionstatechange = () => {
            if (peerConnection.connectionState === 'failed') {
                showError('Connection failed. Please try rejoining the stream.');
            }
        };
        
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        socket.emit('offer', { offer, room: ROOM_ID });

        // Show stop button after starting stream
        const startButton = document.getElementById('startStream');
        const stopButton = document.getElementById('stopStream');
        if (startButton && stopButton) {
            startButton.style.display = 'none';
            stopButton.style.display = 'inline-block';
        }
    } catch (error) {
        console.error('Error starting stream:', error);
        showError('Failed to start stream: ' + error.message);
    }
}

// Stop stream function
function stopStream() {
    try {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            const localVideo = document.getElementById('localVideo');
            if (localVideo) {
                localVideo.srcObject = null;
            }
        }
        if (peerConnection) {
            peerConnection.close();
        }
        
        const startButton = document.getElementById('startStream');
        const stopButton = document.getElementById('stopStream');
        if (startButton && stopButton) {
            startButton.style.display = 'inline-block';
            stopButton.style.display = 'none';
        }
        
        // Notify server that stream has ended
        socket.emit('stream_ended', { room: ROOM_ID });
    } catch (error) {
        console.error('Error stopping stream:', error);
        showError('Failed to stop stream: ' + error.message);
    }
}

// Join stream (for viewers)
socket.on('offer', async data => {
    try {
        peerConnection = new RTCPeerConnection(configuration);
        
        peerConnection.ontrack = event => {
            const remoteVideo = document.getElementById('remoteVideo');
            if (!remoteVideo) {
                throw new Error('Remote video element not found');
            }
            remoteVideo.srcObject = event.streams[0];
        };
        
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                socket.emit('ice_candidate', { candidate: event.candidate, room: ROOM_ID });
            }
        };

        peerConnection.onconnectionstatechange = () => {
            if (peerConnection.connectionState === 'failed') {
                showError('Connection failed. Please try rejoining the stream.');
            }
        };
        
        await peerConnection.setRemoteDescription(data.offer);
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        
        socket.emit('answer', { answer, room: ROOM_ID });
    } catch (error) {
        console.error('Error joining stream:', error);
        showError('Failed to join stream: ' + error.message);
    }
});

// Handle ICE candidates
socket.on('ice_candidate', async data => {
    try {
        if (peerConnection && data.candidate) {
            await peerConnection.addIceCandidate(data.candidate);
        }
    } catch (error) {
        console.error('Error adding ICE candidate:', error);
        showError('Error establishing connection: ' + error.message);
    }
});

// Handle stream ended event
socket.on('stream_ended', () => {
    try {
        if (peerConnection) {
            peerConnection.close();
        }
        const remoteVideo = document.getElementById('remoteVideo');
        if (remoteVideo) {
            remoteVideo.srcObject = null;
        }
        showError('Stream has ended');
    } catch (error) {
        console.error('Error handling stream end:', error);
        showError('Error handling stream end: ' + error.message);
    }
});

// Handle answer from viewer
socket.on('answer', async data => {
    try {
        if (peerConnection && data.answer) {
            await peerConnection.setRemoteDescription(data.answer);
        }
    } catch (error) {
        console.error('Error setting remote description:', error);
        showError('Error establishing connection: ' + error.message);
    }
});

// Initialize buttons when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const streamContainer = document.getElementById('stream-container');
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
