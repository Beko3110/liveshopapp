// Socket.io client initialization
const socket = io();

// Get room ID from stream container if it exists
const streamContainer = document.getElementById('stream-container');
const ROOM_ID = streamContainer ? streamContainer.dataset.roomId : null;

// Initialize analytics tracking
function initAnalytics() {
    if (!ROOM_ID) return;

    // Track viewer join event
    socket.emit('join_stream', { room: ROOM_ID });

    // Set up heartbeat for activity tracking
    let lastActivity = Date.now();
    let isActive = true;

    // Track user activity
    document.addEventListener('mousemove', () => {
        lastActivity = Date.now();
        if (!isActive) {
            isActive = true;
            socket.emit('viewer_activity', { room: ROOM_ID, active: true });
        }
    });

    // Check for inactivity
    setInterval(() => {
        if (isActive && Date.now() - lastActivity > 60000) {
            isActive = false;
            socket.emit('viewer_activity', { room: ROOM_ID, active: false });
        }
    }, 60000);
}

// Handle analytics updates
socket.on('analytics_update', (data) => {
    // Update viewer count
    const viewerCount = document.getElementById('viewerCount');
    if (viewerCount) {
        viewerCount.textContent = data.viewers;
    }

    // Update engagement rate
    const engagementRate = document.getElementById('engagementRate');
    if (engagementRate) {
        engagementRate.textContent = `${data.engagement_rate.toFixed(1)}%`;
    }

    // Update average watch time
    const avgWatchTime = document.getElementById('avgWatchTime');
    if (avgWatchTime) {
        avgWatchTime.textContent = `${Math.floor(data.avg_session_duration / 60)} min`;
    }

    // Update sales metrics
    if (data.revenue_data) {
        const todayRevenue = document.getElementById('todayRevenue');
        if (todayRevenue) {
            todayRevenue.textContent = `$${data.revenue_data.total.toFixed(2)}`;
        }
    }
});

// Initialize analytics when DOM is loaded
document.addEventListener('DOMContentLoaded', initAnalytics);

// Export socket instance and ROOM_ID
export { socket as default, ROOM_ID };
