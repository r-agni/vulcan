import { useState } from 'react';
import styles from './Header.module.css';

const Header = () => {
  const [showOverlayPanel, setShowOverlayPanel] = useState(false);

  return (
    <header className={styles.header}>
      <h1 className={styles.title}>Video AI Surveillance System</h1>
      <div className={styles.toggleControls}>
        <button
          className={styles.toggleBtn}
          onClick={() => setShowOverlayPanel(!showOverlayPanel)}
        >
          Overlay Controls
        </button>
      </div>
    </header>
  );
};

export default Header;
