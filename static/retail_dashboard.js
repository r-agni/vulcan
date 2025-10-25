// Retail Analytics Dashboard JavaScript

let ws = null;
let reconnectInterval = null;
let peakOccupancy = 0;

// Connect to WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 5000);
        }
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(message) {
    const { type, data } = message;

    switch (type) {
        case 'analytics':
            updateAnalytics(data);
            break;
        case 'analysis':
            displayAIAnalysis(data);
            break;
        default:
            console.log('Unknown message type:', type);
    }
}

// Update analytics display
function updateAnalytics(data) {
    // Update store metrics
    const occupancy = data.total_occupancy || 0;
    document.getElementById('total-occupancy').textContent = occupancy;
    document.getElementById('active-trajectories').textContent = data.active_trajectories || 0;

    // Update peak occupancy
    if (occupancy > peakOccupancy) {
        peakOccupancy = occupancy;
        document.getElementById('peak-occupancy').textContent = peakOccupancy;
    }

    // Update zones
    if (data.zones) {
        updateZones(data.zones);
    }

    // Update virtual lines
    if (data.virtual_lines) {
        updateLineCrossingStats(data.virtual_lines);
    }

    // Update queues
    if (data.queues) {
        updateQueues(data.queues);
    }

    // Update alerts
    if (data.alerts) {
        updateAlerts(data.alerts);
    }

    // Update detected persons
    updateDetectedPersons(data.detections_count || 0);
}

// Update zones display
function updateZones(zones) {
    const zoneList = document.getElementById('zone-list');

    if (zones.length === 0) {
        zoneList.innerHTML = '<p class="no-data">No zones configured</p>';
        return;
    }

    zoneList.innerHTML = zones.map(zone => `
        <div class="zone-item" style="border-left-color: ${zone.color}">
            <span class="zone-name">${zone.name}</span>
            <span class="zone-occupancy">${zone.occupancy} people</span>
        </div>
    `).join('');
}

// Update line crossing stats
function updateLineCrossingStats(lines) {
    const statsContainer = document.getElementById('line-crossing-stats');

    if (lines.length === 0) {
        statsContainer.innerHTML = '<p class="no-data">No virtual lines configured</p>';
        return;
    }

    statsContainer.innerHTML = lines.map(line => `
        <div class="line-stat">
            <div class="line-stat-name">${line.name}</div>
            <div class="line-stat-counts">
                <span>↑ In: ${line.counts.in}</span>
                <span>↓ Out: ${line.counts.out}</span>
            </div>
        </div>
    `).join('');
}

// Update queues
function updateQueues(queues) {
    const queueContainer = document.getElementById('queue-analytics');

    if (queues.length === 0) {
        queueContainer.innerHTML = '<p class="no-data">No active queues</p>';
        return;
    }

    queueContainer.innerHTML = queues.map((queue, idx) => `
        <div class="queue-item">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 600; color: #f1f5f9; margin-bottom: 5px;">
                        Queue #${idx + 1}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        ${queue.length} people waiting
                    </div>
                </div>
                <div class="queue-length">${queue.length}</div>
            </div>
        </div>
    `).join('');
}

// Update alerts
function updateAlerts(alerts) {
    const alertsSection = document.getElementById('alerts-section');
    const alertsList = document.getElementById('alerts-list');

    if (alerts.length === 0) {
        alertsSection.style.display = 'none';
        return;
    }

    alertsSection.style.display = 'block';
    alertsList.innerHTML = alerts.map(alert => `
        <div class="alert-item">
            <div class="alert-type">${alert.type}</div>
            <div class="alert-message">${alert.message}</div>
        </div>
    `).join('');
}

// Update detected persons count
function updateDetectedPersons(count) {
    const personsList = document.getElementById('detected-persons-list');

    if (count === 0) {
        personsList.innerHTML = '<p class="no-data">No customers detected</p>';
    } else {
        // Simplified display - in production, you'd get full person details
        personsList.innerHTML = `
            <div class="person-item">
                <div class="person-header">
                    <span class="person-name">${count} Customer${count > 1 ? 's' : ''} Detected</span>
                    <span class="person-badge">ACTIVE</span>
                </div>
                <div class="person-details">
                    <span>Being tracked in real-time</span>
                </div>
            </div>
        `;
    }
}

// Display AI analysis
function displayAIAnalysis(data) {
    const analysisContainer = document.getElementById('ai-analysis');

    const analysisText = data.analysis || 'Analysis in progress...';
    const analysisType = data.analysis_type || 'General';

    // Format analysis text
    let formattedAnalysis = analysisText;

    // Add section breaks for better readability
    formattedAnalysis = formattedAnalysis.replace(/(\d+\.\s+[A-Z\s]+:)/g,
        '<div class="analysis-section-title">$1</div>');

    // Replace bullet points
    formattedAnalysis = formattedAnalysis.replace(/(-\s+)/g, '• ');

    // Replace newlines with breaks
    formattedAnalysis = formattedAnalysis.replace(/\n/g, '<br>');

    analysisContainer.innerHTML = `
        <div style="margin-bottom: 15px;">
            <div style="color: #a78bfa; font-weight: 600; font-size: 12px; text-transform: uppercase;">
                ${analysisType.replace('_', ' ')}
            </div>
            <div style="color: #64748b; font-size: 11px;">
                ${new Date(data.timestamp).toLocaleTimeString()}
            </div>
        </div>
        <div>${formattedAnalysis}</div>
    `;

    // Scroll to top of analysis
    analysisContainer.scrollTop = 0;
}

// Fetch and display heatmap
async function updateHeatmap() {
    try {
        const response = await fetch('/api/heatmap/current');
        const data = await response.json();

        if (data.heatmap) {
            const canvas = document.getElementById('heatmap-canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
            };

            img.src = 'data:image/png;base64,' + data.heatmap;
        }
    } catch (error) {
        console.error('Error fetching heatmap:', error);
    }
}

// Handle overlay control buttons
function setupOverlayControls() {
    const buttons = document.querySelectorAll('.control-btn');

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            button.classList.toggle('active');
            const overlayName = button.dataset.overlay;

            // In production, send WebSocket message to toggle overlay
            console.log(`Toggle overlay: ${overlayName}`, button.classList.contains('active'));
        });
    });
}

// Update current time
function updateTime() {
    const timeElement = document.getElementById('current-time');
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    timeElement.textContent = timeString;
}

// Fetch current analytics
async function fetchCurrentAnalytics() {
    try {
        const response = await fetch('/api/analytics/current');
        const data = await response.json();

        // Update display with current analytics
        if (data.occupancy !== undefined) {
            document.getElementById('total-occupancy').textContent = data.occupancy;
        }

        if (data.zones) {
            updateZones(data.zones);
        }
    } catch (error) {
        console.error('Error fetching analytics:', error);
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Retail Analytics Dashboard...');

    // Connect to WebSocket
    connectWebSocket();

    // Setup overlay controls
    setupOverlayControls();

    // Update time every second
    updateTime();
    setInterval(updateTime, 1000);

    // Fetch current analytics on load
    fetchCurrentAnalytics();

    // Update heatmap every 5 minutes
    updateHeatmap();
    setInterval(updateHeatmap, 300000);

    // Fetch analytics every 10 seconds (backup to WebSocket)
    setInterval(fetchCurrentAnalytics, 10000);

    // Keep WebSocket alive
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
});

// Handle page visibility change
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden');
    } else {
        console.log('Page visible');
        // Refresh analytics when page becomes visible
        fetchCurrentAnalytics();
        updateHeatmap();
    }
});
