import { useState, useEffect } from 'react';
import styles from './CustomerProfile.module.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function CustomerProfile({ profileUuid, onClose }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!profileUuid) return;

    const fetchProfile = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/customers/profile/${profileUuid}`);

        if (!response.ok) {
          throw new Error('Failed to fetch customer profile');
        }

        const data = await response.json();
        setProfile(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [profileUuid]);

  const handleOptOut = async () => {
    if (!window.confirm('Are you sure you want to opt out this customer profile? This action will delete their data in 30 days.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/customers/opt-out/${profileUuid}`, {
        method: 'POST',
      });

      if (response.ok) {
        alert('Customer profile has been opted out successfully');
        onClose();
      }
    } catch (err) {
      alert('Error opting out customer: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className={styles.modal}>
        <div className={styles.modalContent}>
          <div className={styles.loading}>Loading customer profile...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.modal}>
        <div className={styles.modalContent}>
          <div className={styles.error}>Error: {error}</div>
          <button onClick={onClose} className={styles.closeButton}>Close</button>
        </div>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className={styles.modal} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>Customer Profile</h2>
          <button onClick={onClose} className={styles.closeButton}>×</button>
        </div>

        <div className={styles.profileContent}>
          {/* Basic Info */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Basic Information</h3>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.label}>Profile UUID:</span>
                <span className={styles.value}>{profile.profile_uuid}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>VIP Status:</span>
                <span className={`${styles.value} ${profile.vip_status ? styles.vip : ''}`}>
                  {profile.vip_status ? '⭐ VIP' : 'Regular'}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Total Visits:</span>
                <span className={styles.value}>{profile.total_visits}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Visit Frequency:</span>
                <span className={styles.value}>{profile.visit_frequency}</span>
              </div>
            </div>
          </div>

          {/* Visit History */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Visit History</h3>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.label}>First Visit:</span>
                <span className={styles.value}>
                  {profile.first_visit ? new Date(profile.first_visit).toLocaleString() : 'N/A'}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Last Visit:</span>
                <span className={styles.value}>
                  {profile.last_visit ? new Date(profile.last_visit).toLocaleString() : 'N/A'}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Avg Duration:</span>
                <span className={styles.value}>
                  {profile.avg_visit_duration_minutes ? `${Math.round(profile.avg_visit_duration_minutes)} min` : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Behavior Insights */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Behavior Insights</h3>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.label}>Purchase Intent:</span>
                <span className={styles.value}>
                  {profile.avg_purchase_intent_score ? `${Math.round(profile.avg_purchase_intent_score * 100)}%` : 'N/A'}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Favorite Zones:</span>
                <span className={styles.value}>
                  {profile.favorite_zones && profile.favorite_zones.length > 0
                    ? profile.favorite_zones.join(', ')
                    : 'None'}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Preferred Categories:</span>
                <span className={styles.value}>
                  {profile.preferred_product_categories && profile.preferred_product_categories.length > 0
                    ? profile.preferred_product_categories.join(', ')
                    : 'None'}
                </span>
              </div>
            </div>
          </div>

          {/* Recent Visits */}
          {profile.recent_visits && profile.recent_visits.length > 0 && (
            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Recent Visits</h3>
              <div className={styles.visitsList}>
                {profile.recent_visits.map((visit, index) => (
                  <div key={index} className={styles.visitCard}>
                    <div className={styles.visitDate}>
                      {new Date(visit.visit_date).toLocaleString()}
                    </div>
                    <div className={styles.visitDetails}>
                      <span>Duration: {visit.duration_minutes} min</span>
                      <span>Zones: {visit.zones_visited?.join(', ') || 'N/A'}</span>
                      <span>Purchase Intent: {Math.round(visit.purchase_intent_score * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className={styles.actions}>
            <button onClick={handleOptOut} className={styles.optOutButton}>
              Opt Out (GDPR)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CustomerProfile;
