import { useEffect } from 'react';
import useWebSocket from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

function useInventory() {
  const { updateInventory } = useDashboardStore();
  const { lastMessage, isConnected } = useWebSocket('/ws/inventory');

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        updateInventory(data);
      } catch (error) {
        console.error('Error parsing inventory data:', error);
      }
    }
  }, [lastMessage, updateInventory]);

  return { isConnected };
}

export default useInventory;
