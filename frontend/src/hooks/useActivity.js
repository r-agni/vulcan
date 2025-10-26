import { useWebSocket } from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

export const useActivity = () => {
  const addActivity = useDashboardStore((state) => state.addActivity);
  const setConnected = useDashboardStore((state) => state.setConnected);

  const { isConnected } = useWebSocket('/ws/activity', (data) => {
    if (data.type === 'activity' && data.data) {
      addActivity(data.data);
    }
  });

  // Update global connection status
  if (isConnected) {
    setConnected(true);
  }

  return { isConnected };
};

export default useActivity;
