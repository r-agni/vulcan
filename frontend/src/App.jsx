import { useEffect } from 'react';
import Header from './components/Header/Header';
import StatusIndicator from './components/StatusIndicator/StatusIndicator';
import VideoSection from './components/VideoSection/VideoSection';
import ContentPanels from './components/ContentPanels/ContentPanels';
import AlertBanner from './components/AlertBanner/AlertBanner';
import useActivity from './hooks/useActivity';
import useMetrics from './hooks/useMetrics';
import styles from './App.module.css';

function App() {
  // Initialize WebSocket connections
  useActivity();
  useMetrics();

  useEffect(() => {
    // Fade in animation
    document.body.style.opacity = '0';
    setTimeout(() => {
      document.body.style.transition = 'opacity 0.5s ease';
      document.body.style.opacity = '1';
    }, 100);
  }, []);

  return (
    <div className={styles.container}>
      <Header />
      <AlertBanner />

      <div className={styles.mainContent}>
        <VideoSection />
        <ContentPanels />
      </div>

      <StatusIndicator />
    </div>
  );
}

export default App;
