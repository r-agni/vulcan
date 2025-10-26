import { useEffect } from 'react';
import useWebSocket from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

function useInventory() {
  const { updateInventory } = useDashboardStore();
  const { lastMessage, isConnected } = useWebSocket('/ws/inventory');

  // Fetch initial inventory data on mount
  useEffect(() => {
    fetch('/api/inventory/metrics/summary')
      .then(res => res.json())
      .then(data => {
        if (data.type === 'inventory') {
          updateInventory(data.data);
        } else {
          updateInventory(data);
        }
      })
      .catch(error => console.error('Error fetching inventory:', error));
  }, [updateInventory]);

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        if (data.type === 'inventory') {
          updateInventory(data.data);
        } else {
          updateInventory(data);
        }
      } catch (error) {
        console.error('Error parsing inventory data:', error);
      }
    }
  }, [lastMessage, updateInventory]);

  return { isConnected };
}

export default useInventory;
