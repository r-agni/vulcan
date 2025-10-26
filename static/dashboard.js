/**
 * Video AI Surveillance Dashboard - JavaScript
 * WebSocket connections and real-time updates
 */

// WebSocket connections
let activityWS = null;
let analysisWS = null;
let metricsWS = null;
let alertsWS = null;
let inventoryWS = null;
let customersWS = null;

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
    connectAlertsWebSocket();
    connectInventoryWebSocket();
    connectCustomersWebSocket();

    // Setup UI event listeners
    setupOverlayControls();
    setupTogglePanel();

    // Load overlay settings
    loadOverlaySettings();

    // Load initial data for new panels
    loadInventoryData();
    loadCustomerData();

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
 * Connect to Alerts WebSocket
 */
function connectAlertsWebSocket() {
    const wsUrl = `${WS_PROTOCOL}//${WS_HOST}/ws/alerts`;
    console.log('Connecting to alerts stream:', wsUrl);

    alertsWS = new WebSocket(wsUrl);

    alertsWS.onopen = () => {
        console.log('Alerts WebSocket connected');
    };

    alertsWS.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'alerts' && data.data) {
                updateAlerts(data.data);
            }
        } catch (error) {
            console.error('Error parsing alerts message:', error);
        }
    };

    alertsWS.onerror = (error) => {
        console.error('Alerts WebSocket error:', error);
    };

    alertsWS.onclose = () => {
        console.log('Alerts WebSocket closed. Reconnecting in 3s...');
        setTimeout(connectAlertsWebSocket, 3000);
    };
}

/**
 * Connect to Inventory WebSocket
 */
function connectInventoryWebSocket() {
    const wsUrl = `${WS_PROTOCOL}//${WS_HOST}/ws/inventory`;
    console.log('Connecting to inventory stream:', wsUrl);

    inventoryWS = new WebSocket(wsUrl);

    inventoryWS.onopen = () => {
        console.log('Inventory WebSocket connected');
    };

    inventoryWS.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'inventory' && data.data) {
                updateInventoryDisplay(data.data);
            }
        } catch (error) {
            console.error('Error parsing inventory message:', error);
        }
    };

    inventoryWS.onerror = (error) => {
        console.error('Inventory WebSocket error:', error);
    };

    inventoryWS.onclose = () => {
        console.log('Inventory WebSocket closed. Reconnecting in 3s...');
        setTimeout(connectInventoryWebSocket, 3000);
    };
}

/**
 * Connect to Customers WebSocket
 */
function connectCustomersWebSocket() {
    const wsUrl = `${WS_PROTOCOL}//${WS_HOST}/ws/customers`;
    console.log('Connecting to customers stream:', wsUrl);

    customersWS = new WebSocket(wsUrl);

    customersWS.onopen = () => {
        console.log('Customers WebSocket connected');
    };

    customersWS.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'customers' && data.data) {
                updateCustomerStats(data.data);
            }
        } catch (error) {
            console.error('Error parsing customers message:', error);
        }
    };

    customersWS.onerror = (error) => {
        console.error('Customers WebSocket error:', error);
    };

    customersWS.onclose = () => {
        console.log('Customers WebSocket closed. Reconnecting in 3s...');
        setTimeout(connectCustomersWebSocket, 3000);
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
 * Update Alerts Display
 */
function updateAlerts(alerts) {
    const alertBanner = document.getElementById('alert-banner');
    
    // Clear existing alerts
    alertBanner.innerHTML = '';
    
    if (!alerts || alerts.length === 0) {
        alertBanner.style.display = 'none';
        return;
    }
    
    alertBanner.style.display = 'flex';
    
    // Display up to 5 most important alerts
    alerts.slice(0, 5).forEach(alert => {
        const alertCard = createAlertCard(alert);
        alertBanner.appendChild(alertCard);
    });
}

/**
 * Create Alert Card Element
 */
function createAlertCard(alert) {
    const card = document.createElement('div');
    card.className = `alert-card alert-${alert.priority}`;
    card.dataset.alertId = alert.id;

    // Icon and title
    const header = document.createElement('div');
    header.className = 'alert-header';

    const icon = document.createElement('span');
    icon.className = 'alert-icon';
    icon.textContent = getCategoryIcon(alert.category);

    const title = document.createElement('span');
    title.className = 'alert-title';
    title.textContent = alert.title;

    // Add person ID badge if available
    if (alert.person_id) {
        const personBadge = document.createElement('span');
        personBadge.className = 'person-badge';
        personBadge.textContent = `#${alert.person_id}`;
        header.appendChild(icon);
        header.appendChild(title);
        header.appendChild(personBadge);
    } else {
        header.appendChild(icon);
        header.appendChild(title);
    }

    // Message
    const message = document.createElement('div');
    message.className = 'alert-message';
    message.textContent = alert.message;

    // Person details dropdown (if available)
    let detailsSection = null;
    if (alert.person_details && Object.keys(alert.person_details).length > 0) {
        const detailsContainer = document.createElement('div');
        detailsContainer.className = 'alert-details-container';

        const detailsToggle = document.createElement('button');
        detailsToggle.className = 'alert-details-toggle';
        detailsToggle.innerHTML = '<span class="toggle-arrow">▶</span> Show Details';

        detailsSection = document.createElement('div');
        detailsSection.className = 'alert-details-content';
        detailsSection.style.display = 'none';

        // Build details content
        const details = alert.person_details;
        let detailsHTML = '<div class="person-details-grid">';

        if (details.estimated_demographics) {
            detailsHTML += `<div class="detail-item"><strong>Demographics:</strong> ${details.estimated_demographics}</div>`;
        }
        if (details.appearance) {
            detailsHTML += `<div class="detail-item"><strong>Appearance:</strong> ${details.appearance}</div>`;
        }
        if (details.behavior_summary) {
            detailsHTML += `<div class="detail-item"><strong>Behavior:</strong> ${details.behavior_summary}</div>`;
        }
        if (details.zone_history) {
            detailsHTML += `<div class="detail-item"><strong>Zone History:</strong> ${details.zone_history}</div>`;
        }
        if (details.engagement_level) {
            detailsHTML += `<div class="detail-item"><strong>Engagement:</strong> <span class="engagement-${details.engagement_level}">${details.engagement_level.toUpperCase()}</span></div>`;
        }
        if (details.purchase_intent) {
            detailsHTML += `<div class="detail-item"><strong>Purchase Intent:</strong> ${details.purchase_intent}</div>`;
        }
        if (details.recommended_approach) {
            detailsHTML += `<div class="detail-item detail-recommendation"><strong>Recommended Approach:</strong> ${details.recommended_approach}</div>`;
        }

        detailsHTML += '</div>';
        detailsSection.innerHTML = detailsHTML;

        // Toggle functionality
        detailsToggle.onclick = (e) => {
            e.stopPropagation();
            const isExpanded = detailsSection.style.display !== 'none';
            detailsSection.style.display = isExpanded ? 'none' : 'block';
            detailsToggle.innerHTML = isExpanded
                ? '<span class="toggle-arrow">▶</span> Show Details'
                : '<span class="toggle-arrow">▼</span> Hide Details';
            detailsToggle.classList.toggle('expanded', !isExpanded);
        };

        detailsContainer.appendChild(detailsToggle);
        detailsContainer.appendChild(detailsSection);
        message.appendChild(detailsContainer);
    }

    // Footer with recipient badge and dismiss button
    const footer = document.createElement('div');
    footer.className = 'alert-footer';

    const recipientBadge = document.createElement('span');
    recipientBadge.className = `recipient-badge recipient-${alert.recipient}`;
    recipientBadge.textContent = formatRecipient(alert.recipient);

    const dismissBtn = document.createElement('button');
    dismissBtn.className = 'alert-dismiss-btn';
    dismissBtn.textContent = '✕';
    dismissBtn.onclick = () => dismissAlert(alert.id);

    footer.appendChild(recipientBadge);
    footer.appendChild(dismissBtn);

    // Assemble card
    card.appendChild(header);
    card.appendChild(message);
    card.appendChild(footer);

    return card;
}

/**
 * Get Category Icon
 */
function getCategoryIcon(category) {
    const icons = {
        'customer_service': '🛎️',
        'queue_management': '⏱️',
        'security': '🔒',
        'operations': '⚙️',
        'capacity': '👥',
        'system': '💻'
    };
    return icons[category] || 'ℹ️';
}

/**
 * Format Recipient Text
 */
function formatRecipient(recipient) {
    const map = {
        'salesperson': 'Sales',
        'manager': 'Manager',
        'both': 'All Staff'
    };
    return map[recipient] || recipient;
}

/**
 * Dismiss Alert
 */
async function dismissAlert(alertId) {
    try {
        const response = await fetch(`/api/alerts/${alertId}/dismiss`, {
            method: 'POST'
        });
        
        if (response.ok) {
            // Remove alert card with animation
            const card = document.querySelector(`[data-alert-id="${alertId}"]`);
            if (card) {
                card.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => card.remove(), 300);
            }
            console.log(`Alert ${alertId} dismissed`);
        } else {
            console.error('Failed to dismiss alert');
        }
    } catch (error) {
        console.error('Error dismissing alert:', error);
    }
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
 * Load Inventory Data
 */
async function loadInventoryData() {
    try {
        const response = await fetch('/api/inventory/metrics/summary');
        if (response.ok) {
            const data = await response.json();
            updateInventoryDisplay(data);
        }
    } catch (error) {
        console.error('Error loading inventory data:', error);
    }

    // Also load product list
    try {
        const response = await fetch('/api/inventory/products?active_only=true');
        if (response.ok) {
            const products = await response.json();
            displayProductList(products);
        }
    } catch (error) {
        console.error('Error loading product list:', error);
    }
}

/**
 * Update Inventory Display
 */
function updateInventoryDisplay(data) {
    // Update summary stats
    const totalProducts = document.getElementById('inv-total-products');
    const totalViews = document.getElementById('inv-total-views');
    const totalTouches = document.getElementById('inv-total-touches');

    if (totalProducts) totalProducts.textContent = data.total_products || 0;
    if (totalViews) totalViews.textContent = data.total_views || 0;
    if (totalTouches) totalTouches.textContent = data.total_touches || 0;

    // Display most viewed/interacted products
    const inventoryList = document.getElementById('inventory-list');
    if (!inventoryList) return;

    // Clear existing items
    inventoryList.innerHTML = '';

    // Show most interacted products
    const topProducts = data.most_interacted_products || [];

    if (topProducts.length === 0) {
        inventoryList.innerHTML = '<div class="placeholder-text">No product data available</div>';
        return;
    }

    topProducts.forEach(product => {
        const productItem = createProductItem(product);
        inventoryList.appendChild(productItem);
    });
}

/**
 * Display Product List
 */
function displayProductList(products) {
    const inventoryList = document.getElementById('inventory-list');
    if (!inventoryList || products.length === 0) return;

    inventoryList.innerHTML = '';

    products.slice(0, 10).forEach(product => {
        const productItem = createProductItemFromFull(product);
        inventoryList.appendChild(productItem);
    });
}

/**
 * Create Product Item Element (from summary)
 */
function createProductItem(product) {
    const item = document.createElement('div');
    item.className = 'product-item';

    const header = document.createElement('div');
    header.className = 'product-header';

    const name = document.createElement('div');
    name.className = 'product-name';
    name.textContent = product.product_name || 'Unknown Product';

    header.appendChild(name);

    const metrics = document.createElement('div');
    metrics.className = 'product-metrics';
    metrics.innerHTML = `
        <span class="product-metric">👁 ${product.views || 0}</span>
        <span class="product-metric">👆 ${product.interactions || 0}</span>
    `;

    item.appendChild(header);
    item.appendChild(metrics);

    return item;
}

/**
 * Create Product Item Element (from full product)
 */
function createProductItemFromFull(product) {
    const item = document.createElement('div');
    item.className = 'product-item';

    const header = document.createElement('div');
    header.className = 'product-header';

    const name = document.createElement('div');
    name.className = 'product-name';
    name.textContent = product.name || 'Unknown Product';

    const category = document.createElement('span');
    category.className = 'product-category';
    category.textContent = product.category || 'General';

    header.appendChild(name);
    header.appendChild(category);

    item.appendChild(header);

    return item;
}

/**
 * Load Customer Data
 */
async function loadCustomerData() {
    try {
        const response = await fetch('/api/customers/stats');
        if (response.ok) {
            const data = await response.json();
            updateCustomerStats(data);
        }
    } catch (error) {
        console.error('Error loading customer stats:', error);
    }

    // Load customer list
    try {
        const response = await fetch('/api/customers/list?limit=20');
        if (response.ok) {
            const customers = await response.json();
            displayCustomerList(customers);
        }
    } catch (error) {
        console.error('Error loading customer list:', error);
    }
}

/**
 * Update Customer Stats
 */
function updateCustomerStats(data) {
    const totalProfiles = document.getElementById('cust-total-profiles');
    const activeNow = document.getElementById('cust-active-now');
    const vipCount = document.getElementById('cust-vip-count');

    if (totalProfiles) totalProfiles.textContent = data.total_profiles || 0;
    if (activeNow) activeNow.textContent = data.active_visitors || 0;
    if (vipCount) vipCount.textContent = data.vip_customers || 0;
}

/**
 * Display Customer List
 */
function displayCustomerList(customers) {
    const customerList = document.getElementById('customer-list');
    if (!customerList) return;

    customerList.innerHTML = '';

    if (customers.length === 0) {
        customerList.innerHTML = '<div class="placeholder-text">No customer data available</div>';
        return;
    }

    customers.forEach(customer => {
        const customerItem = createCustomerItem(customer);
        customerList.appendChild(customerItem);
    });
}

/**
 * Create Customer Item Element
 */
function createCustomerItem(customer) {
    const item = document.createElement('div');
    item.className = 'customer-item';
    if (customer.vip_status) {
        item.classList.add('vip');
    }

    const header = document.createElement('div');
    header.className = 'customer-header';

    const customerId = document.createElement('div');
    customerId.className = 'customer-id';
    customerId.textContent = `Customer ${customer.profile_uuid ? customer.profile_uuid.substring(0, 8) : 'Unknown'}`;

    header.appendChild(customerId);

    if (customer.vip_status) {
        const vipBadge = document.createElement('span');
        vipBadge.className = 'vip-badge';
        vipBadge.textContent = 'VIP';
        header.appendChild(vipBadge);
    }

    const details = document.createElement('div');
    details.className = 'customer-details';

    // Visit count
    const visitRow = document.createElement('div');
    visitRow.className = 'customer-detail-row';
    visitRow.innerHTML = `
        <span class="detail-label">Visits:</span>
        <span class="detail-value">${customer.total_visits || 0}</span>
    `;
    details.appendChild(visitRow);

    // Frequency
    if (customer.visit_frequency) {
        const freqRow = document.createElement('div');
        freqRow.className = 'customer-detail-row';
        freqRow.innerHTML = `
            <span class="detail-label">Frequency:</span>
            <span class="visit-frequency">${customer.visit_frequency}</span>
        `;
        details.appendChild(freqRow);
    }

    // Purchase intent
    if (customer.purchase_intent_score !== null && customer.purchase_intent_score !== undefined) {
        const intentRow = document.createElement('div');
        intentRow.className = 'customer-detail-row';

        const intentScore = (customer.purchase_intent_score * 100).toFixed(0);
        let intentClass = 'low';
        if (customer.purchase_intent_score >= 0.7) intentClass = 'high';
        else if (customer.purchase_intent_score >= 0.4) intentClass = 'medium';

        intentRow.innerHTML = `
            <span class="detail-label">Intent:</span>
            <div class="purchase-intent">
                <div class="intent-bar">
                    <div class="intent-fill ${intentClass}" style="width: ${intentScore}%"></div>
                </div>
                <span style="font-size: 0.7rem; color: var(--text-secondary);">${intentScore}%</span>
            </div>
        `;
        details.appendChild(intentRow);
    }

    // Last visit
    if (customer.last_visit) {
        const lastVisit = document.createElement('div');
        lastVisit.className = 'last-visit';
        const visitDate = new Date(customer.last_visit);
        lastVisit.textContent = `Last seen: ${formatTimeAgo(visitDate)}`;
        details.appendChild(lastVisit);
    }

    item.appendChild(header);
    item.appendChild(details);

    return item;
}

/**
 * Format time ago helper
 */
function formatTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;

    return date.toLocaleDateString();
}

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
        if (alertsWS && alertsWS.readyState !== WebSocket.OPEN) {
            connectAlertsWebSocket();
        }
        if (inventoryWS && inventoryWS.readyState !== WebSocket.OPEN) {
            connectInventoryWebSocket();
        }
        if (customersWS && customersWS.readyState !== WebSocket.OPEN) {
            connectCustomersWebSocket();
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
    if (alertsWS) alertsWS.close();
    if (inventoryWS) inventoryWS.close();
    if (customersWS) customersWS.close();
});
