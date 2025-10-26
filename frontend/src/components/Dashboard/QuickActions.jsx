import { useState } from 'react';
import styles from './QuickActions.module.css';
import ObservationsPanel from '../ObservationsPanel/ObservationsPanel';

/**
 * Quick Actions Component - Action buttons for dashboard
 * Designed for right panel Actions tab
 */
function QuickActions() {
  const [showObservations, setShowObservations] = useState(false);
  const [observationTarget, setObservationTarget] = useState(null);

  const handleAddObservation = () => {
    const personId = prompt('Enter Person ID:');
    if (personId) {
      setObservationTarget({ personId: parseInt(personId) });
      setShowObservations(true);
    }
  };

  return (
    <div className={styles.quickActions}>
      <h3 className={styles.title}>Quick Actions</h3>

      <div className={styles.actionsGrid}>
        <button
          onClick={handleAddObservation}
          className={styles.actionButton}
        >
          Add Observation
        </button>

        <button
          onClick={() => window.location.href = '#/customers'}
          className={styles.actionButton}
        >
          View Customers
        </button>

        <button
          onClick={() => window.location.href = '#/staff'}
          className={styles.actionButton}
        >
          Manage Staff
        </button>
      </div>

      {/* Observations Modal */}
      {showObservations && observationTarget && (
        <ObservationsPanel
          personId={observationTarget.personId}
          trackingId={observationTarget.trackingId}
          onClose={() => {
            setShowObservations(false);
            setObservationTarget(null);
          }}
          onSaved={() => {
            // Refresh or notify
          }}
        />
      )}
    </div>
  );
}

export default QuickActions;
