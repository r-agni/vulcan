import { useEffect } from 'react';
import useWebSocket from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

function useCustomers() {
  const { updateCustomers } = useDashboardStore();
  const { lastMessage, isConnected } = useWebSocket('/ws/customers');

  // Fetch initial customer stats on mount
  useEffect(() => {
    fetch('/api/customers/stats')
      .then(res => res.json())
      .then(data => {
        if (data.type === 'customers') {
          updateCustomers(data.data);
        } else {
          updateCustomers(data);
        }
      })
      .catch(error => console.error('Error fetching customers:', error));
  }, [updateCustomers]);

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        if (data.type === 'customers') {
          updateCustomers(data.data);
        } else {
          updateCustomers(data);
        }
      } catch (error) {
        console.error('Error parsing customer data:', error);
      }
    }
  }, [lastMessage, updateCustomers]);

  return { isConnected };
}

export default useCustomers;
