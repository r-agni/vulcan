/**
 * RAG Chatbot Functionality for Dashboard
 */

let chatHistory = [];

/**
 * Setup RAG Chatbot
 */
function setupRAGSearch() {
    const searchBtn = document.getElementById('rag-search-btn');
    const queryInput = document.getElementById('rag-query-input');
    const chatMessages = document.getElementById('chat-messages');

    // Setup suggestion buttons
    setupSuggestionButtons();

    // Search button click
    if (searchBtn && queryInput) {
        searchBtn.addEventListener('click', () => {
            performRAGSearch();
        });

        // Enter key to search (Shift+Enter for newline)
        queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                performRAGSearch();
            }
        });

        // Auto-resize textarea
        queryInput.addEventListener('input', () => {
            queryInput.style.height = 'auto';
            queryInput.style.height = queryInput.scrollHeight + 'px';
        });
    }
}

/**
 * Setup suggestion buttons
 */
function setupSuggestionButtons() {
    const suggestionBtns = document.querySelectorAll('.suggestion-btn');
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query');
            const queryInput = document.getElementById('rag-query-input');
            queryInput.value = query;
            performRAGSearch();
        });
    });
}

/**
 * Hide welcome screen
 */
function hideWelcomeScreen() {
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) {
        welcome.style.display = 'none';
    }
}

/**
 * Add a chat message to the UI
 */
function addChatMessage(message, isUser = false, sources = null) {
    hideWelcomeScreen();

    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${isUser ? 'user' : 'assistant'}`;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let sourcesHTML = '';
    if (sources && sources.length > 0) {
        sourcesHTML = `
            <div class="message-sources">
                <div class="sources-header">📚 ${sources.length} source${sources.length > 1 ? 's' : ''}</div>
                ${sources.map((s, i) => `
                    <div class="source-item">
                        <span class="source-ref">[${i+1}]</span> ${formatSourceType(s.type)} - ${Math.round(s.relevance_score * 100)}% match
                    </div>
                `).join('')}
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar ${isUser ? 'user' : 'assistant'}">
            ${isUser ? '👤' : '🤖'}
        </div>
        <div class="message-content">
            <div class="message-bubble">${formatAnswerText(message)}</div>
            ${sourcesHTML}
            <div class="message-timestamp">${timestamp}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Store in history
    chatHistory.push({ message, isUser, timestamp, sources });
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typing-indicator';

    typingDiv.innerHTML = `
        <div class="message-avatar assistant">🤖</div>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;

    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

/**
 * Perform RAG Search
 */
async function performRAGSearch() {
    const queryInput = document.getElementById('rag-query-input');
    const searchBtn = document.getElementById('rag-search-btn');
    const chatStatus = document.getElementById('chat-status');

    const query = queryInput.value.trim();
    if (!query) return;

    // Add user message
    addChatMessage(query, true);

    // Clear input and reset height
    queryInput.value = '';
    queryInput.style.height = 'auto';

    // Show loading state
    searchBtn.disabled = true;
    showTypingIndicator();
    chatStatus.textContent = 'Searching analytics data...';

    try {
        const response = await fetch('/rag/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                n_results: 5
            })
        });

        hideTypingIndicator();

        if (response.ok) {
            const data = await response.json();

            if (data.answer) {
                addChatMessage(data.answer, false, data.sources);
                chatStatus.textContent = '';
            } else {
                addChatMessage('I couldn\'t find any relevant information for that query.', false);
                chatStatus.textContent = '';
            }
        } else {
            hideTypingIndicator();
            addChatMessage('Sorry, there was an error processing your request. Please try again.', false);
            chatStatus.textContent = 'Error occurred';
        }
    } catch (error) {
        console.error('RAG search error:', error);
        hideTypingIndicator();
        addChatMessage('Sorry, I encountered an error: ' + error.message, false);
        chatStatus.textContent = 'Connection error';
    } finally {
        searchBtn.disabled = false;
    }
}

/**
 * Format Answer Text (convert markdown-like formatting)
 */
function formatAnswerText(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/\[Source (\d+)\]/g, '<span class="source-ref">[$1]</span>');
}

/**
 * Format Source Type
 */
function formatSourceType(type) {
    const types = {
        'gemini_report': '🤖 Gemini',
        'behavior_analysis': '👤 Behavior',
        'dwell_time': '⏱️ Dwell Time',
        'queue_metrics': '📊 Queue',
        'alert': '🚨 Alert'
    };
    return types[type] || type;
}

/**
 * Format Timestamp
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Initialize RAG search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    setupRAGSearch();
});
