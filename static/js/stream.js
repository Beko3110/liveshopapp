// Import shared socket instance and ROOM_ID
import socket, { ROOM_ID } from './socket-client.js';

// WebRTC configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
};

// Stream state variables
let localStream;
let peerConnection;
let connectionTimeout;

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
        if (!ROOM_ID) {
            throw new Error('Room ID not found');
        }

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
                reconnectStream();
            }
        };
        
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        socket.emit('offer', { offer, room: ROOM_ID });

        const startButton = document.getElementById('startStream');
        const stopButton = document.getElementById('stopStream');
        if (startButton && stopButton) {
            startButton.style.display = 'none';
            stopButton.style.display = 'inline-block';
        }

        connectionTimeout = setTimeout(() => {
            if (peerConnection.connectionState !== 'connected') {
                showError('Stream connection timeout. Please try again.');
                stopStream();
            }
        }, 30000);

        startAnalytics();
    } catch (error) {
        console.error('Error starting stream:', error);
        showError('Failed to start stream: ' + error.message);
        stopStream();
    }
}

// Analytics tracking
function startAnalytics() {
    let lastActivity = Date.now();
    let isActive = true;

    document.addEventListener('mousemove', () => {
        lastActivity = Date.now();
        if (!isActive) {
            isActive = true;
            socket.emit('viewer_active', { room: ROOM_ID });
        }
    });

    setInterval(() => {
        if (isActive && Date.now() - lastActivity > 60000) {
            isActive = false;
            socket.emit('viewer_inactive', { room: ROOM_ID });
        }
    }, 60000);

    setInterval(() => {
        socket.emit('viewer_heartbeat', { room: ROOM_ID });
    }, 30000);
}

// Reconnect stream function
async function reconnectStream() {
    try {
        if (peerConnection) {
            peerConnection.close();
        }
        await startStream();
    } catch (error) {
        console.error('Error reconnecting stream:', error);
        showError('Failed to reconnect: ' + error.message);
    }
}

// Stop stream function
function stopStream() {
    try {
        if (!ROOM_ID) {
            throw new Error('Room ID not found');
        }

        if (connectionTimeout) {
            clearTimeout(connectionTimeout);
        }

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
        
        socket.emit('stream_ended', { room: ROOM_ID });
    } catch (error) {
        console.error('Error stopping stream:', error);
        showError('Failed to stop stream: ' + error.message);
    }
}

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
    
    if (ROOM_ID) {
        socket.emit('join_room', { room: ROOM_ID });
        if (!document.getElementById('startStream')) {
            startAnalytics();
        }
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

// Handle offer (for viewers)
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
                reconnectStream();
            }
        };
        
        await peerConnection.setRemoteDescription(data.offer);
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        
        socket.emit('answer', { answer, room: ROOM_ID });

        connectionTimeout = setTimeout(() => {
            if (peerConnection.connectionState !== 'connected') {
                showError('Stream connection timeout. Please try again.');
                if (peerConnection) {
                    peerConnection.close();
                }
            }
        }, 30000);
    } catch (error) {
        console.error('Error joining stream:', error);
        showError('Failed to join stream: ' + error.message);
    }
});

// Handle stream ended event
socket.on('stream_ended', () => {
    try {
        if (connectionTimeout) {
            clearTimeout(connectionTimeout);
        }

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

// Handle analytics updates
socket.on('viewer_count_update', data => {
    const viewerCount = document.getElementById('viewerCount');
    if (viewerCount) {
        viewerCount.textContent = data.count;
    }
});

socket.on('engagement_update', data => {
    const engagementMetrics = document.getElementById('engagementMetrics');
    if (engagementMetrics) {
        engagementMetrics.innerHTML = `
            <div>Active Viewers: ${data.activeViewers}</div>
            <div>Engagement Rate: ${data.engagementRate}%</div>
            <div>Average Watch Time: ${Math.floor(data.avgWatchTime / 60)} minutes</div>
        `;
    }
});

export { startStream, stopStream };
