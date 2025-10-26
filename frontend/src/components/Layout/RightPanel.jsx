import { useState } from 'react';
import styles from './Layout.module.css';

/**
 * Tabbed right panel component
 * Displays contextual information based on selected tab
 */
function RightPanel({ tabs = [], defaultTab = 0 }) {
  const [activeTabIndex, setActiveTabIndex] = useState(defaultTab);

  if (!tabs || tabs.length === 0) {
    return null;
  }

  return (
    <div className={styles.rightPanelContainer}>
      {/* Tab Headers */}
      {tabs.length > 1 && (
        <div className={styles.tabHeaders}>
          {tabs.map((tab, index) => (
            <button
              key={index}
              className={`${styles.tabHeader} ${activeTabIndex === index ? styles.active : ''}`}
              onClick={() => setActiveTabIndex(index)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Tab Content */}
      <div className={styles.tabContent}>
        {tabs[activeTabIndex]?.content}
      </div>
    </div>
  );
}

export default RightPanel;
