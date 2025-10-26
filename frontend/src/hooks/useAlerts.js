import { useEffect } from 'react';
import useWebSocket from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

function useAlerts() {
  const { setAlerts } = useDashboardStore();
  const { lastMessage, isConnected } = useWebSocket('/ws/alerts');

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        if (data.alerts) {
          setAlerts(data.alerts);
        }
      } catch (error) {
        console.error('Error parsing alerts:', error);
      }
    }
  }, [lastMessage, setAlerts]);

  return { isConnected };
}

export default useAlerts;
