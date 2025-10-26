import styles from './StatsPanel.module.css';
import useDashboardStore from '../../store/dashboardStore';

/**
 * Stats Panel Component - Shows inventory and customer analytics
 * Designed for right panel Stats tab
 */
function StatsPanel() {
  const { inventory, customers } = useDashboardStore();

  return (
    <div className={styles.statsPanel}>
      {/* Inventory Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Product Inventory</h3>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{inventory.total_products || 0}</div>
            <div className={styles.statLabel}>Products</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{inventory.total_views || 0}</div>
            <div className={styles.statLabel}>Views</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{inventory.total_touches || 0}</div>
            <div className={styles.statLabel}>Touches</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{inventory.total_pickups || 0}</div>
            <div className={styles.statLabel}>Pickups</div>
          </div>
        </div>

        {inventory.most_viewed_products && inventory.most_viewed_products.length > 0 && (
          <div className={styles.productList}>
            <h4 className={styles.subTitle}>Most Viewed</h4>
            {inventory.most_viewed_products.slice(0, 5).map((product, index) => (
              <div key={index} className={styles.productItem}>
                <span className={styles.productName}>{product.name}</span>
                <span className={styles.productViews}>{product.views}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Customer Analytics Section */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Customer Analytics</h3>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{customers.total_profiles || 0}</div>
            <div className={styles.statLabel}>Profiles</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{customers.vip_customers || 0}</div>
            <div className={styles.statLabel}>VIP</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{customers.active_visitors || 0}</div>
            <div className={styles.statLabel}>Active</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{customers.recent_visitors_7d || 0}</div>
            <div className={styles.statLabel}>Recent (7d)</div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default StatsPanel;
