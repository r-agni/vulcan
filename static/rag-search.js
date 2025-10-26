/**
 * RAG Search Functionality - Simple & Clean
 */

/**
 * Setup RAG Search
 */
function setupRAGSearch() {
    const searchBtn = document.getElementById('rag-search-btn');
    const queryInput = document.getElementById('rag-query-input');

    if (searchBtn && queryInput) {
        // Search button click
        searchBtn.addEventListener('click', () => {
            performRAGSearch();
        });

        // Enter key to search
        queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
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
    const searchBtn = document.getElementById('rag-search-btn');
    const responseDiv = document.getElementById('rag-response');

    const query = queryInput.value.trim();
    if (!query) return;

    // Show loading state
    searchBtn.disabled = true;
    responseDiv.innerHTML = '<span class="rag-loading">Searching analytics data</span>';

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

            if (data.answer) {
                // Clear response div and stream the answer
                responseDiv.innerHTML = '';
                streamText(responseDiv, formatAnswerText(data.answer));
            } else {
                responseDiv.innerHTML = '<em>No relevant information found for your query.</em>';
            }
        } else {
            responseDiv.innerHTML = '<em style="color: #E94B3C;">Error processing request. Please try again.</em>';
        }
    } catch (error) {
        console.error('RAG search error:', error);
        responseDiv.innerHTML = '<em style="color: #E94B3C;">Connection error: ' + error.message + '</em>';
    } finally {
        searchBtn.disabled = false;
    }
}

/**
 * Stream text with typewriter effect
 */
function streamText(element, text, speed = 15) {
    let index = 0;
    element.innerHTML = '';

    function type() {
        if (index < text.length) {
            element.innerHTML += text.charAt(index);
            index++;
            element.scrollTop = element.scrollHeight;
            setTimeout(type, speed);
        }
    }

    type();
}

/**
 * Format Answer Text (convert markdown-like formatting)
 */
function formatAnswerText(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// Initialize RAG search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    setupRAGSearch();
});
