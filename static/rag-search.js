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

    // Show loading state with animation
    searchBtn.disabled = true;
    const loadingSteps = [
        'Searching analytics data...',
        'Retrieving relevant documents...',
        'Generating answer with AI...'
    ];
    let loadingStep = 0;

    responseDiv.innerHTML = '<span class="rag-loading">' + loadingSteps[0] + '</span>';

    // Animate loading steps
    const loadingInterval = setInterval(() => {
        loadingStep = (loadingStep + 1) % loadingSteps.length;
        const loadingElement = responseDiv.querySelector('.rag-loading');
        if (loadingElement) {
            loadingElement.textContent = loadingSteps[loadingStep];
        }
    }, 2000);

    try {
        const startTime = Date.now();

        const response = await fetch('/rag/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                n_results: 5
            })
        });

        clearInterval(loadingInterval);
        const responseTime = ((Date.now() - startTime) / 1000).toFixed(1);

        console.log('[RAG] Response received:', response.status, response.statusText);

        if (response.ok) {
            const data = await response.json();
            console.log('[RAG] Data received:', data);

            if (data.answer) {
                console.log('[RAG] Answer length:', data.answer.length);
                console.log('[RAG] Answer preview:', data.answer.substring(0, 100));

                // Clear response div and stream the answer
                responseDiv.innerHTML = '';
                console.log('[RAG] Response div cleared, starting to display answer');

                // Show performance info if available
                if (data.performance) {
                    const perfInfo = document.createElement('div');
                    perfInfo.style.fontSize = '0.8em';
                    perfInfo.style.color = '#888';
                    perfInfo.style.marginBottom = '10px';
                    perfInfo.textContent = `Retrieved ${data.retrieved_docs} documents in ${responseTime}s`;
                    responseDiv.appendChild(perfInfo);

                    const answerDiv = document.createElement('div');
                    responseDiv.appendChild(answerDiv);
                    streamText(answerDiv, formatAnswerText(data.answer));
                } else {
                    streamText(responseDiv, formatAnswerText(data.answer));
                }

                console.log('[RAG] Answer display initiated');
            } else {
                console.log('[RAG] No answer in response');
                responseDiv.innerHTML = '<em>No relevant information found for your query.</em>';
            }
        } else {
            console.error('[RAG] Response not OK:', response.status);
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.detail || 'Error processing request. Please try again.';
            console.error('[RAG] Error message:', errorMsg);
            responseDiv.innerHTML = `<em style="color: #E94B3C;">${errorMsg}</em>`;
        }
    } catch (error) {
        clearInterval(loadingInterval);
        console.error('RAG search error:', error);

        let errorMessage = 'Connection error: ' + error.message;
        if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Unable to connect to the server. Please ensure the RAG service is running.';
        }

        responseDiv.innerHTML = `<em style="color: #E94B3C;">${errorMessage}</em>`;
    } finally {
        searchBtn.disabled = false;
    }
}

/**
 * Stream text with typewriter effect
 */
function streamText(element, text, speed = 15) {
    console.log('[RAG] streamText called with text length:', text.length);
    console.log('[RAG] Target element:', element);

    let index = 0;
    element.innerHTML = '';

    function type() {
        if (index < text.length) {
            element.innerHTML += text.charAt(index);
            index++;
            element.scrollTop = element.scrollHeight;
            setTimeout(type, speed);
        } else {
            console.log('[RAG] Streaming complete');
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
