import { useState, useRef, useEffect } from 'react';
import styles from './ChatPanel.module.css';
import useDashboardStore from '../../store/dashboardStore';
import useChat from '../../hooks/useChat';

function ChatPanel() {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const { chatMessages, sessionId } = useDashboardStore();
  const { sendMessage, initSession } = useChat();

  useEffect(() => {
    // Initialize chat session on mount
    if (!sessionId) {
      initSession();
    }
  }, [sessionId, initSession]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading) return;

    setIsLoading(true);
    await sendMessage(inputValue);
    setInputValue('');
    setIsLoading(false);
  };

  const suggestedQuestions = [
    "What is the current occupancy?",
    "Show product interaction trends",
    "Analyze customer behavior",
    "What products are most popular?",
  ];

  const handleSuggestionClick = (question) => {
    setInputValue(question);
  };

  return (
    <div className={styles.chatPanel}>
      <div className={styles.header}>
        <h2 className={styles.title}>AI Assistant</h2>
        <span className={styles.status}>
          {sessionId ? '● Online' : '○ Offline'}
        </span>
      </div>

      <div className={styles.messagesContainer}>
        {chatMessages.length === 0 ? (
          <div className={styles.emptyState}>
            <p className={styles.welcomeText}>
              Ask me anything about your store analytics!
            </p>
            <div className={styles.suggestions}>
              <p className={styles.suggestionsLabel}>Try asking:</p>
              {suggestedQuestions.map((question, index) => (
                <button
                  key={index}
                  className={styles.suggestionButton}
                  onClick={() => handleSuggestionClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {chatMessages.map((message, index) => (
              <div
                key={index}
                className={`${styles.message} ${styles[message.role]}`}
              >
                <div className={styles.messageHeader}>
                  <span className={styles.role}>
                    {message.role === 'user' ? 'You' : 'AI Assistant'}
                  </span>
                  <span className={styles.timestamp}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className={styles.messageContent}>
                  {message.content}
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div className={styles.sources}>
                    <span className={styles.sourcesLabel}>Sources:</span>
                    {message.sources.slice(0, 3).map((source, idx) => (
                      <span key={idx} className={styles.source}>
                        {source.type} - {source.timestamp}
                      </span>
                    ))}
                  </div>
                )}
                {message.visualization && (
                  <div className={styles.visualization}>
                    <img
                      src={`data:image/png;base64,${message.visualization}`}
                      alt="Chart visualization"
                      className={styles.chart}
                    />
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <form className={styles.inputForm} onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Ask about your store analytics..."
          className={styles.input}
          disabled={isLoading || !sessionId}
        />
        <button
          type="submit"
          className={styles.submitButton}
          disabled={isLoading || !sessionId || !inputValue.trim()}
        >
          {isLoading ? 'Thinking...' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default ChatPanel;
