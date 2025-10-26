import { useEffect, useState } from 'react';
import Header from './components/Header/Header';
import StatusIndicator from './components/StatusIndicator/StatusIndicator';
import VideoSection from './components/VideoSection/VideoSection';
import AlertBanner from './components/AlertBanner/AlertBanner';
import CustomerList from './components/CustomerList/CustomerList';
import StaffDashboard from './components/StaffDashboard/StaffDashboard';
import OverlayControls from './components/OverlayControls/OverlayControls';
import TimelineViewer from './components/TimelineViewer/TimelineViewer';
import ThreeColumnLayout from './components/Layout/ThreeColumnLayout';
import RightPanel from './components/Layout/RightPanel';
import ActivityFeed from './components/Dashboard/ActivityFeed';
import StatsPanel from './components/Dashboard/StatsPanel';
import QuickActions from './components/Dashboard/QuickActions';
import ChatPanel from './components/ChatPanel/ChatPanel';
import useActivity from './hooks/useActivity';
import useMetrics from './hooks/useMetrics';
import useInventory from './hooks/useInventory';
import useCustomers from './hooks/useCustomers';
import useAnalysis from './hooks/useAnalysis';
import useDashboardStore from './store/dashboardStore';
import styles from './App.module.css';

function App() {
  const [activeView, setActiveView] = useState('dashboard'); // dashboard, customers, staff, settings
  const [showTimeline, setShowTimeline] = useState(false);

  // Initialize WebSocket connections
  useActivity();
  useMetrics();
  useInventory();
  useCustomers();
  useAnalysis();

  useEffect(() => {
    // Fade in animation
    document.body.style.opacity = '0';
    setTimeout(() => {
      document.body.style.transition = 'opacity 0.5s ease';
      document.body.style.opacity = '1';
    }, 100);
  }, []);

  const renderContent = () => {
    const { analysisText } = useDashboardStore();

    switch (activeView) {
      case 'dashboard':
        return (
          <ThreeColumnLayout
            left={<ActivityFeed />}
            center={
              <div>
                <VideoSection />
                <div style={{ padding: '20px' }}>
                  <h2 style={{
                    fontFamily: "'Playfair Display', serif",
                    fontSize: '20px',
                    color: '#ffffff',
                    marginBottom: '16px',
                    paddingBottom: '12px',
                    borderBottom: '1px solid rgba(255,255,255,0.1)'
                  }}>
                    AI Analysis
                  </h2>
                  <p style={{
                    fontFamily: "'Cormorant Garamond', serif",
                    fontSize: '15px',
                    lineHeight: '1.6',
                    color: '#ffffff',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {analysisText || 'Waiting for analysis...'}
                  </p>
                </div>
              </div>
            }
            right={
              <RightPanel
                tabs={[
                  { label: 'Stats', content: <StatsPanel /> },
                  { label: 'Chat', content: <ChatPanel /> },
                  { label: 'Actions', content: <QuickActions /> }
                ]}
              />
            }
          />
        );
      case 'customers':
        return (
          <ThreeColumnLayout
            left={<ActivityFeed />}
            center={<CustomerList />}
            right={<div style={{ padding: '20px', color: '#ffffff', fontFamily: "'Cormorant Garamond', serif" }}>Select a customer to view details</div>}
          />
        );
      case 'staff':
        return (
          <ThreeColumnLayout
            left={<ActivityFeed />}
            center={<StaffDashboard />}
            hideRight={true}
          />
        );
      case 'settings':
        return (
          <ThreeColumnLayout
            left={<ActivityFeed />}
            center={<OverlayControls />}
            hideRight={true}
          />
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
