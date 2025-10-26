import { useEffect, useState } from 'react';
import Header from './components/Header/Header';
import StatusIndicator from './components/StatusIndicator/StatusIndicator';
import VideoSection from './components/VideoSection/VideoSection';
import ContentPanels from './components/ContentPanels/ContentPanels';
import AlertBanner from './components/AlertBanner/AlertBanner';
import CustomerList from './components/CustomerList/CustomerList';
import StaffDashboard from './components/StaffDashboard/StaffDashboard';
import OverlayControls from './components/OverlayControls/OverlayControls';
import TimelineViewer from './components/TimelineViewer/TimelineViewer';
import useActivity from './hooks/useActivity';
import useMetrics from './hooks/useMetrics';
import styles from './App.module.css';

function App() {
  const [activeView, setActiveView] = useState('dashboard'); // dashboard, customers, staff, settings
  const [showTimeline, setShowTimeline] = useState(false);

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

  const renderContent = () => {
    switch (activeView) {
      case 'dashboard':
        return (
          <div className={styles.mainContent}>
            <VideoSection />
            <ContentPanels />
          </div>
        );
      case 'customers':
        return (
          <div className={styles.fullWidthContent}>
            <CustomerList />
          </div>
        );
      case 'staff':
        return (
          <div className={styles.fullWidthContent}>
            <StaffDashboard />
          </div>
        );
      case 'settings':
        return (
          <div className={styles.fullWidthContent}>
            <OverlayControls />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className={styles.container}>
      <Header />
      <AlertBanner />

      {/* Navigation Tabs */}
      <div className={styles.navTabs}>
        <button
          className={`${styles.navTab} ${activeView === 'dashboard' ? styles.active : ''}`}
          onClick={() => setActiveView('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={`${styles.navTab} ${activeView === 'customers' ? styles.active : ''}`}
          onClick={() => setActiveView('customers')}
        >
          Customers
        </button>
        <button
          className={`${styles.navTab} ${activeView === 'staff' ? styles.active : ''}`}
          onClick={() => setActiveView('staff')}
        >
          Staff
        </button>
        <button
          className={`${styles.navTab} ${activeView === 'settings' ? styles.active : ''}`}
          onClick={() => setActiveView('settings')}
        >
          Settings
        </button>
        <button
          className={styles.navTab}
          onClick={() => setShowTimeline(true)}
        >
          Timeline
        </button>
      </div>

      {renderContent()}

      <StatusIndicator />

      {/* Timeline Modal */}
      {showTimeline && (
        <TimelineViewer
          type="scene"
          onClose={() => setShowTimeline(false)}
        />
      )}
    </div>
  );
}

export default App;
