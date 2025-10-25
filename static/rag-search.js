/**
 * RAG Search Functionality for Dashboard
 */

/**
 * Setup RAG Search
 */
function setupRAGSearch() {
    const searchBtn = document.getElementById('rag-search-btn');
    const queryInput = document.getElementById('rag-query-input');
    const resultsDiv = document.getElementById('rag-results');
    const toggleRagBtn = document.getElementById('toggle-rag');
    const ragSearch = document.getElementById('rag-search');

    // Toggle RAG panel
    if (toggleRagBtn && ragSearch) {
        toggleRagBtn.addEventListener('click', () => {
            ragSearch.classList.toggle('collapsed');
            const arrow = toggleRagBtn.querySelector('span');
            arrow.textContent = ragSearch.classList.contains('collapsed') ? '▶' : '▼';
        });
    }

    // Search button click
    if (searchBtn && queryInput) {
        searchBtn.addEventListener('click', () => performRAGSearch());
        
        // Enter key to search
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performRAGSearch();
            }
        });
    }
}

/**
 * Perform RAG Search
 */
async function performRAGSearch() {
    const queryInput = document.getElementById('rag-query-input');
    const resultsDiv = document.getElementById('rag-results');
    const searchBtn = document.getElementById('rag-search-btn');
    
    const query = queryInput.value.trim();
    if (!query) return;
    
    // Show loading state
    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching...';
    resultsDiv.innerHTML = '<div class="rag-loading">🔍 Searching analytics data...</div>';
    
    try {
        const response = await fetch('/rag/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                n_results: 5
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            displayRAGResults(data);
        } else {
            resultsDiv.innerHTML = '<div class="rag-error">❌ Search failed. Please try again.</div>';
        }
    } catch (error) {
        console.error('RAG search error:', error);
        resultsDiv.innerHTML = '<div class="rag-error">❌ Error: ' + error.message + '</div>';
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = 'Search';
    }
}

/**
 * Display RAG Search Results
 */
function displayRAGResults(data) {
    const resultsDiv = document.getElementById('rag-results');
    
    if (!data.answer) {
        resultsDiv.innerHTML = '<div class="rag-error">No results found.</div>';
        return;
    }
    
    // Create results HTML
    let html = `
        <div class="rag-answer">
            <div class="rag-answer-header">📊 Answer:</div>
            <div class="rag-answer-text">${formatAnswerText(data.answer)}</div>
        </div>
    `;
    
    // Add sources if available
    if (data.sources && data.sources.length > 0) {
        html += '<div class="rag-sources">';
        html += '<div class="rag-sources-header">📚 Sources (' + data.sources.length + '):</div>';
        html += '<div class="rag-sources-list">';
        
        data.sources.forEach((source, idx) => {
            const relevance = Math.round(source.relevance_score * 100);
            html += `
                <div class="rag-source-item">
                    <span class="source-number">[${idx + 1}]</span>
                    <span class="source-type">${formatSourceType(source.type)}</span>
                    <span class="source-relevance">${relevance}%</span>
                    <div class="source-timestamp">${formatTimestamp(source.timestamp)}</div>
                </div>
            `;
        });
        
        html += '</div></div>';
    }
    
    resultsDiv.innerHTML = html;
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
