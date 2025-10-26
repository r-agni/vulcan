import styles from './ActivityFeed.module.css';
import useDashboardStore from '../../store/dashboardStore';

/**
 * Activity Feed Component - Shows real-time activity stream
 * Designed for left sidebar
 */
function ActivityFeed() {
  const { activities } = useDashboardStore();

  return (
    <div className={styles.activityFeed}>
      <h2 className={styles.title}>Activity Feed</h2>
      <div className={styles.activityList}>
        {activities.length === 0 ? (
          <div className={styles.emptyState}>No recent activity</div>
        ) : (
          activities.map((activity, index) => (
            <div key={index} className={styles.activityItem}>
              <span className={styles.activityTime}>
                {new Date(activity.timestamp).toLocaleTimeString()}
              </span>
              <span className={styles.activityMessage}>{activity.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default ActivityFeed;
