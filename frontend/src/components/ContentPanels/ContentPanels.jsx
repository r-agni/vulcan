import styles from './ContentPanels.module.css';
import useDashboardStore from '../../store/dashboardStore';
import useInventory from '../../hooks/useInventory';
import useCustomers from '../../hooks/useCustomers';
import useAnalysis from '../../hooks/useAnalysis';
import ChatPanel from '../ChatPanel/ChatPanel';

function ContentPanels() {
  const { activities, analysisText, inventory, customers } = useDashboardStore();

  // Connect to WebSocket streams
  useInventory();
  useCustomers();
  useAnalysis();

  return (
    <div className={styles.contentPanels}>
      {/* Activity Feed Panel */}
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Activity Feed</h2>
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

      {/* AI Analysis Panel */}
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>AI Analysis</h2>
        <div className={styles.analysisContent}>
          {analysisText ? (
            <p className={styles.analysisText}>{analysisText}</p>
          ) : (
            <div className={styles.emptyState}>Waiting for analysis...</div>
          )}
        </div>
      </div>

      {/* Inventory Panel */}
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Product Inventory</h2>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Products</div>
            <div className={styles.statValue}>{inventory.total_products || 0}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Views</div>
            <div className={styles.statValue}>{inventory.total_views || 0}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Touches</div>
            <div className={styles.statValue}>{inventory.total_touches || 0}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Pickups</div>
            <div className={styles.statValue}>{inventory.total_pickups || 0}</div>
          </div>
        </div>
        {inventory.most_viewed_products && inventory.most_viewed_products.length > 0 && (
          <div className={styles.productList}>
            <h3 className={styles.subTitle}>Most Viewed Products</h3>
            {inventory.most_viewed_products.slice(0, 5).map((product, index) => (
              <div key={index} className={styles.productItem}>
                <span className={styles.productName}>{product.name}</span>
                <span className={styles.productViews}>{product.views} views</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Customer Analytics Panel */}
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Customer Analytics</h2>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Profiles</div>
            <div className={styles.statValue}>{customers.total_profiles || 0}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>VIP Customers</div>
            <div className={styles.statValue}>{customers.vip_customers || 0}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Active Visitors</div>
            <div className={styles.statValue}>{customers.active_visitors || 0}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Recent (7d)</div>
            <div className={styles.statValue}>{customers.recent_visitors_7d || 0}</div>
          </div>
        </div>
      </div>

      {/* Chat Panel */}
      <div className={`${styles.panel} ${styles.chatPanelContainer}`}>
        <ChatPanel />
      </div>
    </div>
  );
}

export default ContentPanels;
