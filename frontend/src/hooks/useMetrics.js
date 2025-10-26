import { useEffect } from 'react';
import { useWebSocket } from './useWebSocket';
import useDashboardStore from '../store/dashboardStore';

export const useMetrics = () => {
  const updateMetrics = useDashboardStore((state) => state.updateMetrics);

  // Fetch initial metrics on mount
  useEffect(() => {
    // Since there's no dedicated metrics endpoint, initialize with zeros
    // The WebSocket will provide real-time updates
    updateMetrics({
      occupancy: 0,
      peak_today: 0,
      avg_dwell_time: 0,
      active_trajectories: 0,
      total_entries: 0,
      active_zones: 0,
    });
  }, [updateMetrics]);

  const { isConnected } = useWebSocket('/ws/metrics', (data) => {
    if (data.type === 'metrics' && data.data) {
      updateMetrics(data.data);
    }
  });

  return { isConnected };
};

export default useMetrics;
