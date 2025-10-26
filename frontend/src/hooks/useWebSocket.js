import { useEffect, useRef, useState } from 'react';

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_HOST = window.location.host;

export const useWebSocket = (endpoint, onMessage, options = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const { reconnectDelay = 3000, enabled = true } = options;

  // Store onMessage in a ref to avoid stale closures
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    if (!enabled) return;

    const connect = () => {
      const wsUrl = `${WS_PROTOCOL}//${WS_HOST}${endpoint}`;
      console.log(`Connecting to ${wsUrl}`);

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log(`WebSocket connected: ${endpoint}`);
        setIsConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          setLastMessage(event.data);
          if (onMessageRef.current) {
            const data = JSON.parse(event.data);
            onMessageRef.current(data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error(`WebSocket error on ${endpoint}:`, error);
        setIsConnected(false);
      };

      ws.current.onclose = () => {
        console.log(`WebSocket closed: ${endpoint}. Reconnecting in ${reconnectDelay}ms...`);
        setIsConnected(false);

        // Schedule reconnection
        reconnectTimeout.current = setTimeout(() => {
          connect();
        }, reconnectDelay);
      };
    };

    connect();

    // Cleanup function
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [endpoint, reconnectDelay, enabled]);

  const sendMessage = (data) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  };

  return { isConnected, sendMessage, lastMessage };
};

export default useWebSocket;
