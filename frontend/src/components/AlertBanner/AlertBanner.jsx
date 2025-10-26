import { useEffect } from 'react';
import styles from './AlertBanner.module.css';
import useDashboardStore from '../../store/dashboardStore';
import useAlerts from '../../hooks/useAlerts';

function AlertBanner() {
  const { alerts, dismissAlert } = useDashboardStore();
  useAlerts(); // Connect to alerts WebSocket

  // Get the most recent high-priority alert
  const currentAlert = alerts.length > 0
    ? alerts.sort((a, b) => {
        const priorityOrder = { high: 3, medium: 2, low: 1 };
        return (priorityOrder[b.priority] || 0) - (priorityOrder[a.priority] || 0);
      })[0]
    : null;

  useEffect(() => {
    if (currentAlert) {
      // Auto-dismiss after 10 seconds
      const timer = setTimeout(() => {
        dismissAlert(currentAlert.alert_id);
      }, 10000);

      return () => clearTimeout(timer);
    }
  }, [currentAlert, dismissAlert]);

  if (!currentAlert) return null;

  const handleDismiss = () => {
    dismissAlert(currentAlert.alert_id);
  };

  const getPriorityClass = (priority) => {
    switch (priority) {
      case 'high':
        return styles.high;
      case 'medium':
        return styles.medium;
      case 'low':
        return styles.low;
      default:
        return styles.medium;
    }
  };

  return (
    <div className={`${styles.alertBanner} ${getPriorityClass(currentAlert.priority)}`}>
      <div className={styles.alertContent}>
        <div className={styles.alertIcon}>
          {currentAlert.priority === 'high' ? '⚠' : 'ℹ'}
        </div>
        <div className={styles.alertMessage}>
          <strong>{currentAlert.alert_type}:</strong> {currentAlert.message}
        </div>
        <button
          className={styles.dismissButton}
          onClick={handleDismiss}
          aria-label="Dismiss alert"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export default AlertBanner;
