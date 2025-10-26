import { create } from 'zustand';

const useDashboardStore = create((set) => ({
  // Connection status
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),

  // Metrics
  metrics: {
    occupancy: 0,
    peak_today: 0,
    avg_dwell_time: 0,
    active_trajectories: 0,
    total_entries: 0,
    active_zones: 0,
  },
  updateMetrics: (metrics) => set({ metrics }),

  // Activity feed
  activities: [],
  addActivity: (activity) =>
    set((state) => ({
      activities: [activity, ...state.activities].slice(0, 50),
    })),

  // Analysis
  analysisText: '',
  analysisId: null,
  updateAnalysis: (data) =>
    set((state) => {
      if (data.analysis_id !== state.analysisId) {
        return {
          analysisId: data.analysis_id,
          analysisText: data.text || '',
        };
      }
      return {
        analysisText: state.analysisText + (data.text || ''),
      };
    }),

  // Alerts
  alerts: [],
  setAlerts: (alerts) => set({ alerts }),
  dismissAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.filter((a) => a.id !== alertId),
    })),

  // Inventory
  inventory: {
    total_products: 0,
    total_views: 0,
    total_touches: 0,
    total_pickups: 0,
    most_viewed_products: [],
    most_interacted_products: [],
  },
  updateInventory: (inventory) => set({ inventory }),

  // Customers
  customers: {
    total_profiles: 0,
    vip_customers: 0,
    total_visits: 0,
    recent_visitors_7d: 0,
    active_visitors: 0,
  },
  customerList: [],
  updateCustomers: (customers) => set({ customers }),
  setCustomerList: (customerList) => set({ customerList }),

  // Overlay settings
  overlaySettings: {
    bounding_boxes: true,
    trajectories: true,
    zones: true,
    virtual_lines: true,
    heatmap: false,
    proximity: true,
    labels: true,
    alerts: true,
  },
  toggleOverlay: (overlayName) =>
    set((state) => ({
      overlaySettings: {
        ...state.overlaySettings,
        [overlayName]: !state.overlaySettings[overlayName],
      },
    })),
}));

export default useDashboardStore;
