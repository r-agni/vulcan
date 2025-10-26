import styles from './Layout.module.css';

/**
 * Three-column layout component for dashboard views
 * Provides consistent left sidebar, center content, and right panel structure
 */
function ThreeColumnLayout({ left, center, right, hideLeft = false, hideRight = false }) {
  return (
    <div className={styles.threeColumnLayout}>
      {!hideLeft && (
        <aside className={styles.leftSidebar}>
          {left}
        </aside>
      )}

      <main className={`${styles.centerContent} ${hideLeft ? styles.noLeft : ''} ${hideRight ? styles.noRight : ''}`}>
        {center}
      </main>

      {!hideRight && (
        <aside className={styles.rightPanel}>
          {right}
        </aside>
      )}
    </div>
  );
}

export default ThreeColumnLayout;
