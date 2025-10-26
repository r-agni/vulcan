import { useState, useEffect } from 'react';
import styles from './OverlayControls.module.css';
import useDashboardStore from '../../store/dashboardStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function OverlayControls() {
  const { overlaySettings, toggleOverlay } = useDashboardStore();
  const [syncing, setSyncing] = useState(false);

  const overlayOptions = [
    { key: 'bounding_boxes', label: 'Bounding Boxes', icon: '⬜', description: 'Show person detection boxes' },
    { key: 'trajectories', label: 'Trajectories', icon: '📍', description: 'Show movement paths' },
    { key: 'zones', label: 'Zones', icon: '🏪', description: 'Show defined zones' },
    { key: 'virtual_lines', label: 'Virtual Lines', icon: '➖', description: 'Show crossing detection lines' },
    { key: 'heatmap', label: 'Heatmap', icon: '🔥', description: 'Show activity heatmap' },
    { key: 'proximity', label: 'Proximity', icon: '👥', description: 'Show proximity indicators' },
    { key: 'labels', label: 'Labels', icon: '🏷️', description: 'Show text labels' },
    { key: 'alerts', label: 'Alerts', icon: '⚠️', description: 'Show alert indicators' },
  ];

  const handleToggle = async (overlayKey) => {
    // Update local state immediately
    toggleOverlay(overlayKey);

    // Sync with backend
    try {
      setSyncing(true);
      const newValue = !overlaySettings[overlayKey];

      const response = await fetch(
        `${API_BASE_URL}/api/overlay/toggle?overlay_name=${overlayKey}&enabled=${newValue}`,
        { method: 'POST' }
      );

      if (!response.ok) {
        console.error('Failed to sync overlay setting with backend');
        // Revert on failure
        toggleOverlay(overlayKey);
      }
    } catch (error) {
      console.error('Error syncing overlay:', error);
      // Revert on failure
      toggleOverlay(overlayKey);
    } finally {
      setSyncing(false);
    }
  };

  const handleToggleAll = async (enabled) => {
    overlayOptions.forEach(option => {
      if (overlaySettings[option.key] !== enabled) {
        toggleOverlay(option.key);
      }
    });

    // Sync all with backend
    try {
      setSyncing(true);
      await Promise.all(
        overlayOptions.map(option =>
          fetch(
            `${API_BASE_URL}/api/overlay/toggle?overlay_name=${option.key}&enabled=${enabled}`,
            { method: 'POST' }
          )
        )
      );
    } catch (error) {
      console.error('Error syncing overlays:', error);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className={styles.overlayControls}>
      <div className={styles.header}>
        <h3 className={styles.title}>Video Overlay Controls</h3>
        <div className={styles.bulkActions}>
          <button
            onClick={() => handleToggleAll(true)}
            className={styles.bulkButton}
            disabled={syncing}
          >
            Enable All
          </button>
          <button
            onClick={() => handleToggleAll(false)}
            className={styles.bulkButton}
            disabled={syncing}
          >
            Disable All
          </button>
        </div>
      </div>

      <div className={styles.overlayGrid}>
        {overlayOptions.map((option) => (
          <div
            key={option.key}
            className={`${styles.overlayCard} ${overlaySettings[option.key] ? styles.enabled : ''}`}
            onClick={() => handleToggle(option.key)}
          >
            <div className={styles.overlayIcon}>{option.icon}</div>
            <div className={styles.overlayInfo}>
              <div className={styles.overlayLabel}>{option.label}</div>
              <div className={styles.overlayDescription}>{option.description}</div>
            </div>
            <div className={styles.toggleSwitch}>
              <input
                type="checkbox"
                checked={overlaySettings[option.key]}
                onChange={() => handleToggle(option.key)}
                className={styles.checkbox}
                disabled={syncing}
              />
              <span className={styles.slider} />
            </div>
          </div>
        ))}
      </div>

      {syncing && (
        <div className={styles.syncIndicator}>
          Syncing with server...
        </div>
      )}
    </div>
  );
}

export default OverlayControls;
