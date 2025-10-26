import { useCallback } from 'react';
import useDashboardStore from '../store/dashboardStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const useChat = () => {
  const { sessionId, setSessionId, addChatMessage } = useDashboardStore();

  const initSession = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/rag/chat/session/new`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to create chat session');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      console.log('Chat session initialized:', data.session_id);
    } catch (error) {
      console.error('Error initializing chat session:', error);
    }
  }, [setSessionId]);

  const sendMessage = useCallback(
    async (message) => {
      if (!sessionId) {
        console.error('No active session');
        return;
      }

      // Add user message to UI immediately
      addChatMessage({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      });

      try {
        const response = await fetch(`${API_BASE_URL}/rag/chat/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: message,
            session_id: sessionId,
            n_results: 5,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to send message');
        }

        const data = await response.json();

        // Add assistant response to UI
        addChatMessage({
          role: 'assistant',
          content: data.answer,
          timestamp: new Date().toISOString(),
          sources: data.sources || [],
          visualization: data.visualization || null,
          intent: data.intent || null,
        });
      } catch (error) {
        console.error('Error sending message:', error);

        // Add error message to UI
        addChatMessage({
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          timestamp: new Date().toISOString(),
          isError: true,
        });
      }
    },
    [sessionId, addChatMessage]
  );

  return {
    initSession,
    sendMessage,
  };
};

export default useChat;
