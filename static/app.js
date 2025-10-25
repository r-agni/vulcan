// WebSocket connection
let ws = null;
let reconnectInterval = null;

// Connect to WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateStatus('Connected', true);
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
        updateStatus('Connection Error', false);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateStatus('Disconnected', false);

        // Attempt to reconnect
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 5000);
        }
    };
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(message) {
    const { type, data } = message;

    switch (type) {
        case 'detection':
            displayPersonProfile(data);
            break;
        case 'analysis':
            displayAnalysis(data);
            break;
        default:
            console.log('Unknown message type:', type);
    }
}

// Display person profile in sidebar
function displayPersonProfile(person) {
    const noDetection = document.getElementById('no-detection');
    const personProfile = document.getElementById('person-profile');
    const detectionOverlay = document.getElementById('detection-overlay');

    // Hide no detection message
    noDetection.classList.add('hidden');
    personProfile.classList.remove('hidden');

    // Update profile information
    document.getElementById('profile-name').textContent = person.name;
    document.getElementById('profile-id').textContent = person.id;
    document.getElementById('visit-count').textContent = person.visit_count;
    document.getElementById('first-seen').textContent = formatDateTime(person.first_seen);
    document.getElementById('last-seen').textContent = formatDateTime(person.last_seen);

    // Update thumbnail
    if (person.thumbnail) {
        document.getElementById('profile-thumbnail').src = '/' + person.thumbnail;
    }

    // Show NEW badge for new persons
    const newBadge = document.getElementById('new-badge');
    if (person.is_new) {
        newBadge.classList.remove('hidden');
    } else {
        newBadge.classList.add('hidden');
    }

    // Update video overlay
    const badge = detectionOverlay.querySelector('.detection-badge');
    badge.textContent = `Person Detected: ${person.name}`;
    badge.classList.add('active');

    // Show analysis status
    const analysisStatus = document.getElementById('analysis-status');
    const analysisContent = document.getElementById('analysis-content');
    analysisStatus.innerHTML = '<p>Analyzing behavior...</p><div class="spinner"></div>';
    analysisContent.classList.add('hidden');
}

// Display behavior analysis
function displayAnalysis(analysisData) {
    const analysisStatus = document.getElementById('analysis-status');
    const analysisContent = document.getElementById('analysis-content');
    const behaviorAnalysis = document.getElementById('behavior-analysis');

    // Hide status, show content
    analysisStatus.classList.add('hidden');
    analysisContent.classList.remove('hidden');

    // Update analysis text
    behaviorAnalysis.textContent = analysisData.analysis;

    // Format the analysis text for better readability
    formatAnalysisText(behaviorAnalysis);
}

// Format analysis text with proper structure
function formatAnalysisText(element) {
    let text = element.textContent;

    // Add some basic formatting
    text = text.replace(/(\d+\.\s+[A-Z\s]+:)/g, '\n\n$1\n');
    text = text.replace(/(-\s+)/g, '\n  - ');

    element.textContent = text;
}

// Update connection status
function updateStatus(statusText, isConnected) {
    const statusTextElement = document.getElementById('status-text');
    const statusIndicator = document.querySelector('.status-indicator');

    statusTextElement.textContent = statusText;

    if (isConnected) {
        statusIndicator.style.background = '#10b981';
    } else {
        statusIndicator.style.background = '#ef4444';
    }
}

// Format date and time
function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Load all persons from database
async function loadAllPersons() {
    try {
        const response = await fetch('/api/persons');
        const persons = await response.json();

        const personGrid = document.getElementById('person-grid');
        const personCount = document.getElementById('person-count');

        // Update count
        personCount.textContent = `${persons.length} person${persons.length !== 1 ? 's' : ''} in database`;

        // Clear grid
        personGrid.innerHTML = '';

        // Add person cards
        persons.forEach(person => {
            const card = createPersonCard(person);
            personGrid.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading persons:', error);
    }
}

// Create person card element
function createPersonCard(person) {
    const card = document.createElement('div');
    card.className = 'person-card';
    card.onclick = () => viewPersonDetails(person.id);

    const thumbnail = person.thumbnail || '/static/default-avatar.png';

    card.innerHTML = `
        <img src="/${thumbnail}" alt="${person.name}" onerror="this.src='/static/default-avatar.png'">
        <h4>${person.name}</h4>
        <p>Visits: ${person.visit_count}</p>
        <p>Last: ${formatDateTime(person.last_seen)}</p>
    `;

    return card;
}

// View person details
async function viewPersonDetails(personId) {
    try {
        const response = await fetch(`/api/person/${personId}`);
        const person = await response.json();

        if (person.error) {
            alert(person.error);
            return;
        }

        // Display in sidebar
        displayPersonProfile({
            id: person.id,
            name: person.name,
            visit_count: person.visit_count,
            first_seen: person.first_seen,
            last_seen: person.last_seen,
            thumbnail: person.thumbnail,
            is_new: false
        });

        // Display recent analyses if available
        if (person.recent_analyses && person.recent_analyses.length > 0) {
            const latestAnalysis = person.recent_analyses[0];
            displayAnalysis({
                person_id: person.id,
                analysis: latestAnalysis.text,
                timestamp: latestAnalysis.timestamp
            });
        }

    } catch (error) {
        console.error('Error loading person details:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Video AI Dashboard...');

    // Connect to WebSocket
    connectWebSocket();

    // Load all persons
    loadAllPersons();

    // Refresh persons every 30 seconds
    setInterval(loadAllPersons, 30000);

    // Keep WebSocket alive with ping
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
});
