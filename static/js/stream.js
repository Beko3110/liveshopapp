// Import shared socket instance
import socket from './socket-client.js';

// WebRTC configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
};

let localStream;
let peerConnection;

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
                socket.emit('ice_candidate', event.candidate);
            }
        };
        
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        socket.emit('offer', offer);

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
}

// Join stream (for viewers)
socket.on('offer', async offer => {
    try {
        peerConnection = new RTCPeerConnection(configuration);
        
        peerConnection.ontrack = event => {
            document.getElementById('remoteVideo').srcObject = event.streams[0];
        };
        
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                socket.emit('ice_candidate', event.candidate);
            }
        };
        
        await peerConnection.setRemoteDescription(offer);
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        
        socket.emit('answer', answer);
    } catch (error) {
        console.error('Error joining stream:', error);
    }
});

// Handle ICE candidates
socket.on('ice_candidate', async candidate => {
    try {
        await peerConnection.addIceCandidate(candidate);
    } catch (error) {
        console.error('Error adding ICE candidate:', error);
    }
});

// Initialize buttons when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const startStreamBtn = document.getElementById('startStream');
    const stopStreamBtn = document.getElementById('stopStream');
    if (startStreamBtn) {
        startStreamBtn.addEventListener('click', startStream);
    }
    if (stopStreamBtn) {
        stopStreamBtn.addEventListener('click', stopStream);
    }
});
