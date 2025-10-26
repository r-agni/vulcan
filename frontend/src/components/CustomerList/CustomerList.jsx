import { useState, useEffect } from 'react';
import styles from './CustomerList.module.css';
import CustomerProfile from '../CustomerProfile/CustomerProfile';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function CustomerList() {
  const [customers, setCustomers] = useState([]);
  const [recentVisits, setRecentVisits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('all'); // all, active, vip
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProfile, setSelectedProfile] = useState(null);

  useEffect(() => {
    fetchCustomers();
    fetchRecentVisits();
  }, []);

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/customers/list?limit=50`);
      if (response.ok) {
        const data = await response.json();
        setCustomers(data);
      }
    } catch (error) {
      console.error('Error fetching customers:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentVisits = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/customers/recent-visits?hours=24&limit=20`);
      if (response.ok) {
        const data = await response.json();
        setRecentVisits(data);
      }
    } catch (error) {
      console.error('Error fetching recent visits:', error);
    }
  };

  const filteredCustomers = customers.filter(customer => {
    // Filter by tab
    if (activeTab === 'active') {
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
      const lastVisit = new Date(customer.last_visit);
      if (lastVisit < oneHourAgo) return false;
    }
    if (activeTab === 'vip' && !customer.vip_status) {
      return false;
    }

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        customer.profile_uuid?.toLowerCase().includes(search) ||
        customer.favorite_zones?.some(zone => zone.toLowerCase().includes(search)) ||
        customer.preferred_categories?.some(cat => cat.toLowerCase().includes(search))
      );
    }

    return true;
  });

  const getVisitFrequencyColor = (frequency) => {
    if (!frequency) return '#666';
    if (frequency === 'daily') return '#00ff00';
    if (frequency === 'weekly') return '#00d4ff';
    if (frequency === 'monthly') return '#ff9900';
    return '#888';
  };

  const formatDuration = (minutes) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  return (
    <div className={styles.customerList}>
      <div className={styles.header}>
        <h2 className={styles.title}>Customer Management</h2>
        <button onClick={fetchCustomers} className={styles.refreshButton}>
          🔄 Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'all' ? styles.active : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All Customers ({customers.length})
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'active' ? styles.active : ''}`}
          onClick={() => setActiveTab('active')}
        >
          Active Now
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'vip' ? styles.active : ''}`}
          onClick={() => setActiveTab('vip')}
        >
          VIP ({customers.filter(c => c.vip_status).length})
        </button>
      </div>

      {/* Search */}
      <div className={styles.searchBar}>
        <input
          type="text"
          placeholder="Search by UUID, zones, or categories..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={styles.searchInput}
        />
      </div>

      {/* Customer Cards */}
      <div className={styles.customerGrid}>
        {loading ? (
          <div className={styles.loading}>Loading customers...</div>
        ) : filteredCustomers.length === 0 ? (
          <div className={styles.emptyState}>No customers found</div>
        ) : (
          filteredCustomers.map((customer) => (
            <div
              key={customer.id}
              className={`${styles.customerCard} ${customer.vip_status ? styles.vip : ''}`}
              onClick={() => setSelectedProfile(customer.profile_uuid)}
            >
              <div className={styles.cardHeader}>
                <span className={styles.customerId}>
                  {customer.profile_uuid.slice(0, 8)}...
                </span>
                {customer.vip_status && <span className={styles.vipBadge}>⭐ VIP</span>}
              </div>

              <div className={styles.stats}>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Visits</span>
                  <span className={styles.statValue}>{customer.total_visits}</span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Frequency</span>
                  <span
                    className={styles.statValue}
                    style={{ color: getVisitFrequencyColor(customer.visit_frequency) }}
                  >
                    {customer.visit_frequency || 'Unknown'}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Avg Duration</span>
                  <span className={styles.statValue}>
                    {formatDuration(customer.avg_visit_duration)}
                  </span>
                </div>
              </div>

              <div className={styles.metrics}>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Purchase Intent:</span>
                  <div className={styles.progressBar}>
                    <div
                      className={styles.progressFill}
                      style={{ width: `${(customer.purchase_intent_score || 0) * 100}%` }}
                    />
                  </div>
                  <span className={styles.metricValue}>
                    {Math.round((customer.purchase_intent_score || 0) * 100)}%
                  </span>
                </div>
              </div>

              {customer.favorite_zones && customer.favorite_zones.length > 0 && (
                <div className={styles.zones}>
                  <strong>Zones:</strong> {customer.favorite_zones.slice(0, 3).join(', ')}
                  {customer.favorite_zones.length > 3 && ' ...'}
                </div>
              )}

              <div className={styles.cardFooter}>
                <span className={styles.lastVisit}>
                  Last: {customer.last_visit ? new Date(customer.last_visit).toLocaleString() : 'N/A'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Recent Visits Section */}
      <div className={styles.recentSection}>
        <h3 className={styles.sectionTitle}>Recent Visits (24h)</h3>
        <div className={styles.visitsList}>
          {recentVisits.length === 0 ? (
            <div className={styles.emptyState}>No recent visits</div>
          ) : (
            recentVisits.map((visit, index) => (
              <div key={index} className={styles.visitCard}>
                <div className={styles.visitHeader}>
                  <span className={styles.visitId}>{visit.profile_uuid?.slice(0, 8)}...</span>
                  {visit.vip_status && <span className={styles.vipBadge}>⭐</span>}
                  <span className={styles.visitTime}>
                    {new Date(visit.visit_date).toLocaleTimeString()}
                  </span>
                </div>
                <div className={styles.visitDetails}>
                  <span>Duration: {visit.duration_minutes}m</span>
                  <span>Intent: {Math.round(visit.purchase_intent_score * 100)}%</span>
                  {visit.zones_visited && (
                    <span>Zones: {visit.zones_visited.slice(0, 2).join(', ')}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Customer Profile Modal */}
      {selectedProfile && (
        <CustomerProfile
          profileUuid={selectedProfile}
          onClose={() => setSelectedProfile(null)}
        />
      )}
    </div>
  );
}

export default CustomerList;
