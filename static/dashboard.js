/**
 * Video AI Surveillance Dashboard - JavaScript
 * WebSocket connections and real-time updates
 */

// WebSocket connections
let activityWS = null;
let analysisWS = null;
let metricsWS = null;

// Configuration
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_HOST = window.location.host;

// State
let currentAnalysisId = null;
let overlaySettings = {};

/**
 * Initialize Dashboard
 */
function initDashboard() {
    console.log('Initializing Video AI Dashboard...');

    // Connect WebSockets
    connectActivityWebSocket();
    connectAnalysisWebSocket();
    connectMetricsWebSocket();

    // Setup UI event listeners
    setupOverlayControls();
    setupTogglePanel();
    setupAnalysisToggle();

    // Load overlay settings
    loadOverlaySettings();

    console.log('Dashboard initialized');
}

/**
 * Connect to Activity WebSocket
 */
function connectActivityWebSocket() {
    const wsUrl = `${WS_PROTOCOL}//${WS_HOST}/ws/activity`;
    console.log('Connecting to activity stream:', wsUrl);

    activityWS = new WebSocket(wsUrl);

    activityWS.onopen = () => {
        console.log('Activity WebSocket connected');
        updateConnectionStatus(true);
    };

    activityWS.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'activity' && data.data) {
                addActivityItem(data.data);
            }
        } catch (error) {
            console.error('Error parsing activity message:', error);
        }
    };

    activityWS.onerror = (error) => {
        console.error('Activity WebSocket error:', error);
        updateConnectionStatus(false);
    };

    activityWS.onclose = () => {
        console.log('Activity WebSocket closed. Reconnecting in 3s...');
        updateConnectionStatus(false);
        setTimeout(connectActivityWebSocket, 3000);
    };
}

/**
 * Connect to Analysis WebSocket
 */
function connectAnalysisWebSocket() {
    const wsUrl = `${WS_PROTOCOL}//${WS_HOST}/ws/analysis`;
    console.log('Connecting to analysis stream:', wsUrl);

    analysisWS = new WebSocket(wsUrl);

    analysisWS.onopen = () => {
        console.log('Analysis WebSocket connected');
    };

    analysisWS.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'analysis_stream' && data.data) {
                updateAnalysis(data.data);
            }
        } catch (error) {
            console.error('Error parsing analysis message:', error);
        }
    };

    analysisWS.onerror = (error) => {
        console.error('Analysis WebSocket error:', error);
    };

    analysisWS.onclose = () => {
        console.log('Analysis WebSocket closed. Reconnecting in 3s...');
        setTimeout(connectAnalysisWebSocket, 3000);
    };
}

/**
 * Connect to Metrics WebSocket
 */
function connectMetricsWebSocket() {
    const wsUrl = `${WS_PROTOCOL}//${WS_HOST}/ws/metrics`;
    console.log('Connecting to metrics stream:', wsUrl);

    metricsWS = new WebSocket(wsUrl);

    metricsWS.onopen = () => {
        console.log('Metrics WebSocket connected');
    };

    metricsWS.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'metrics' && data.data) {
                updateMetrics(data.data);
            }
        } catch (error) {
            console.error('Error parsing metrics message:', error);
        }
    };

    metricsWS.onerror = (error) => {
        console.error('Metrics WebSocket error:', error);
    };

    metricsWS.onclose = () => {
        console.log('Metrics WebSocket closed. Reconnecting in 3s...');
        setTimeout(connectMetricsWebSocket, 3000);
    };
}

/**
 * Add Activity Item to Feed
 */
function addActivityItem(activity) {
    const feed = document.getElementById('activity-feed');

    // Remove placeholder if exists
    const placeholder = feed.querySelector('.activity-item');
    if (placeholder && placeholder.textContent.includes('initializing')) {
        feed.innerHTML = '';
    }

    // Create activity item
    const item = document.createElement('div');
    item.className = 'activity-item';

    const icon = document.createElement('span');
    icon.className = 'activity-icon';
    icon.textContent = '●';

    const text = document.createElement('span');
    text.className = 'activity-text';
    text.textContent = activity.message;

    item.appendChild(icon);
    item.appendChild(text);

    // Add to feed (prepend for newest first)
    feed.insertBefore(item, feed.firstChild);

    // Limit to 50 items
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }

    // Auto-scroll to top
    feed.scrollTop = 0;
}

/**
 * Update Analysis Display
 */
function updateAnalysis(analysisData) {
    const analysisFeed = document.getElementById('analysis-feed');

    // If new analysis session, clear previous
    if (analysisData.analysis_id !== currentAnalysisId) {
        currentAnalysisId = analysisData.analysis_id;
        analysisFeed.innerHTML = '';
    }

    // Remove placeholder
    const placeholder = analysisFeed.querySelector('.analysis-placeholder');
    if (placeholder) {
        analysisFeed.innerHTML = '';
    }

    // Append or update text
    if (analysisData.text) {
        const textNode = document.createTextNode(analysisData.text + '\n\n');
        analysisFeed.appendChild(textNode);
    }

    // Auto-scroll to bottom
    analysisFeed.scrollTop = analysisFeed.scrollHeight;

    // If analysis is complete, add visual indicator
    if (analysisData.is_complete) {
        const completeIndicator = document.createElement('div');
        completeIndicator.style.cssText = 'color: #b0b0b0; font-style: italic; margin-top: 1rem; text-align: right;';
        completeIndicator.textContent = '— Analysis Complete —';
        analysisFeed.appendChild(completeIndicator);
    }
}

/**
 * Update Metrics Display
 */
function updateMetrics(metrics) {
    // Update each metric value
    const occupancy = document.getElementById('metric-occupancy');
    const peak = document.getElementById('metric-peak');
    const dwell = document.getElementById('metric-dwell');
    const tracking = document.getElementById('metric-tracking');
    const entries = document.getElementById('metric-entries');
    const zones = document.getElementById('metric-zones');

    if (occupancy) occupancy.textContent = metrics.occupancy || 0;
    if (peak) peak.textContent = metrics.peak_today || 0;
    
    // Format dwell time
    if (dwell) {
        const dwellTime = metrics.avg_dwell_time || 0;
        if (dwellTime >= 60) {
            const mins = Math.floor(dwellTime / 60);
            const secs = Math.floor(dwellTime % 60);
            dwell.textContent = `${mins}m ${secs}s`;
        } else {
            dwell.textContent = `${Math.floor(dwellTime)}s`;
        }
    }
    
    if (tracking) tracking.textContent = metrics.active_trajectories || 0;
    if (entries) entries.textContent = metrics.total_entries || 0;
    if (zones) zones.textContent = metrics.active_zones || 0;

    // Add pulse animation to updated values
    [occupancy, peak, dwell, tracking, entries, zones].forEach(el => {
        if (el) {
            el.style.animation = 'none';
            setTimeout(() => {
                el.style.animation = 'pulse 0.5s ease';
            }, 10);
        }
    });
}

/**
 * Update Connection Status
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('status-indicator');
    const statusText = indicator.querySelector('.status-text');

    if (connected) {
        indicator.classList.remove('disconnected');
        indicator.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        indicator.classList.remove('connected');
        indicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

/**
 * Setup Overlay Controls
 */
function setupOverlayControls() {
    const overlayPanel = document.getElementById('overlay-settings');
    const checkboxes = overlayPanel.querySelectorAll('input[type="checkbox"]');

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', async (e) => {
            const overlayName = e.target.name;
            const enabled = e.target.checked;

            // Update overlay via API
            try {
                const response = await fetch(`/api/overlay/toggle?overlay_name=${overlayName}&enabled=${enabled}`, {
                    method: 'POST'
                });

                if (response.ok) {
                    console.log(`Overlay '${overlayName}' ${enabled ? 'enabled' : 'disabled'}`);
                } else {
                    console.error('Failed to toggle overlay');
                    // Revert checkbox state
                    e.target.checked = !enabled;
                }
            } catch (error) {
                console.error('Error toggling overlay:', error);
                e.target.checked = !enabled;
            }
        });
    });
}

/**
 * Setup Toggle Panel Button
 */
function setupTogglePanel() {
    const toggleBtn = document.getElementById('toggle-panel');
    const overlayPanel = document.getElementById('overlay-settings');

    toggleBtn.addEventListener('click', () => {
        overlayPanel.classList.toggle('active');
    });

    // Close panel when clicking outside
    document.addEventListener('click', (e) => {
        if (!overlayPanel.contains(e.target) && e.target !== toggleBtn) {
            overlayPanel.classList.remove('active');
        }
    });
}

/**
 * Setup Live Analysis Toggle
 */
function setupAnalysisToggle() {
    const toggleBtn = document.getElementById('toggle-analysis');
    const analysisFeed = document.getElementById('analysis-feed');

    if (toggleBtn && analysisFeed) {
        toggleBtn.addEventListener('click', () => {
            analysisFeed.classList.toggle('collapsed');
            const arrow = toggleBtn.querySelector('span');
            
            // Toggle arrow direction
            if (analysisFeed.classList.contains('collapsed')) {
                arrow.textContent = '▶';
            } else {
                arrow.textContent = '▼';
            }
        });
    }
}

/**
 * Load Overlay Settings from API
 */
async function loadOverlaySettings() {
    try {
        const response = await fetch('/api/overlay/settings');
        if (response.ok) {
            overlaySettings = await response.json();
            console.log('Loaded overlay settings:', overlaySettings);

            // Update checkboxes to match settings
            const overlayPanel = document.getElementById('overlay-settings');
            const checkboxes = overlayPanel.querySelectorAll('input[type="checkbox"]');

            checkboxes.forEach(checkbox => {
                const overlayName = checkbox.name;
                if (overlaySettings.hasOwnProperty(overlayName)) {
                    checkbox.checked = overlaySettings[overlayName];
                }
            });
        }
    } catch (error) {
        console.error('Error loading overlay settings:', error);
    }
}

/**
 * Fetch Recent Activity on Load
 */
async function loadRecentActivity() {
    try {
        const response = await fetch('/api/activity/recent?limit=20');
        if (response.ok) {
            const activities = await response.json();
            const feed = document.getElementById('activity-feed');
            feed.innerHTML = '';

            // Add activities in reverse order (newest first)
            activities.reverse().forEach(activity => {
                addActivityItem(activity);
            });
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

/**
 * Initialize on Page Load
 */
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    loadRecentActivity();

    // Add smooth fade-in animation
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
});

/**
 * Handle Page Visibility Change
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden - pausing updates');
    } else {
        console.log('Page visible - resuming updates');
        // Reconnect if needed
        if (activityWS.readyState !== WebSocket.OPEN) {
            connectActivityWebSocket();
        }
        if (analysisWS.readyState !== WebSocket.OPEN) {
            connectAnalysisWebSocket();
        }
        if (metricsWS.readyState !== WebSocket.OPEN) {
            connectMetricsWebSocket();
        }
    }
});

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {
    if (activityWS) activityWS.close();
    if (analysisWS) analysisWS.close();
    if (metricsWS) metricsWS.close();
});
