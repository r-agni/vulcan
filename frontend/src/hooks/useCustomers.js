import { useEffect } from 'react';
import useWebSocket from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

function useCustomers() {
  const { updateCustomers } = useDashboardStore();
  const { lastMessage, isConnected } = useWebSocket('/ws/customers');

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        updateCustomers(data);
      } catch (error) {
        console.error('Error parsing customer data:', error);
      }
    }
  }, [lastMessage, updateCustomers]);

  return { isConnected };
}

export default useCustomers;
