// WebRTC configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
};

let localStream;
let peerConnection;
const socket = io();

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
    } catch (error) {
        console.error('Error starting stream:', error);
    }
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
