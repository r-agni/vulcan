import { useEffect, useState } from 'react';
import useDashboardStore from '../../store/dashboardStore';
import styles from './StatusIndicator.module.css';

function StatusIndicator() {
  const isConnected = useDashboardStore((state) => state.isConnected);
  const [showIndicator, setShowIndicator] = useState(true);

  useEffect(() => {
    // Hide indicator after 3 seconds if connected
    if (isConnected) {
      const timer = setTimeout(() => {
        setShowIndicator(false);
      }, 3000);
      return () => clearTimeout(timer);
    } else {
      setShowIndicator(true);
    }
  }, [isConnected]);

  if (!showIndicator && isConnected) return null;

  return (
    <div className={`${styles.statusIndicator} ${isConnected ? styles.connected : styles.disconnected}`}>
      <div className={styles.indicator}>
        <span className={styles.dot}></span>
        <span className={styles.text}>
          {isConnected ? 'Connected' : 'Connecting...'}
        </span>
      </div>
    </div>
  );
}

export default StatusIndicator;
