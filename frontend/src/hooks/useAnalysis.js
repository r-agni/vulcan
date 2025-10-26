import { useEffect } from 'react';
import useWebSocket from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

function useAnalysis() {
  const { updateAnalysis } = useDashboardStore();
  const { lastMessage, isConnected } = useWebSocket('/ws/analysis');

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        updateAnalysis(data);
      } catch (error) {
        console.error('Error parsing analysis data:', error);
      }
    }
  }, [lastMessage, updateAnalysis]);

  return { isConnected };
}

export default useAnalysis;
