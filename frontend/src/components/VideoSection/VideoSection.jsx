import { useEffect, useRef } from 'react';
import styles from './VideoSection.module.css';
import useDashboardStore from '../../store/dashboardStore';

function VideoSection() {
  const imgRef = useRef(null);
  const { metrics } = useDashboardStore();

  useEffect(() => {
    // Force reload the video feed image periodically
    const interval = setInterval(() => {
      if (imgRef.current) {
        imgRef.current.src = `/video_feed?t=${Date.now()}`;
      }
    }, 100); // Refresh every 100ms for smooth video

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.videoSection}>
      <div className={styles.videoContainer}>
        <img
          ref={imgRef}
          src="/video_feed"
          alt="Live video feed"
          className={styles.videoFeed}
          onError={(e) => {
            // On error, retry after a delay
            setTimeout(() => {
              e.target.src = `/video_feed?t=${Date.now()}`;
            }, 1000);
          }}
        />
        <div className={styles.metricsOverlay}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Occupancy</div>
            <div className={styles.metricValue}>{metrics.occupancy || 0}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Avg Dwell Time</div>
            <div className={styles.metricValue}>
              {metrics.avg_dwell_time ? `${Math.round(metrics.avg_dwell_time)}s` : '0s'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Total Entries</div>
            <div className={styles.metricValue}>{metrics.total_entries || 0}</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>Active Zones</div>
            <div className={styles.metricValue}>{metrics.active_zones || 0}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VideoSection;
