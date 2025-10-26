import { useWebSocket } from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

export const useMetrics = () => {
  const updateMetrics = useDashboardStore((state) => state.updateMetrics);

  const { isConnected } = useWebSocket('/ws/metrics', (data) => {
    if (data.type === 'metrics' && data.data) {
      updateMetrics(data.data);
    }
  });

  return { isConnected };
};

export default useMetrics;
