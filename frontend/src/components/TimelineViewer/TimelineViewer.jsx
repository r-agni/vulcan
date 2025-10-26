import { useState, useEffect } from 'react';
import styles from './TimelineViewer.module.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function TimelineViewer({ type = 'person', id, onClose }) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // all, detections, analyses, observations

  useEffect(() => {
    if (!id) return;

    const fetchTimeline = async () => {
      try {
        setLoading(true);
        let url;

        if (type === 'person') {
          url = `${API_BASE_URL}/api/person/${id}/timeline`;
        } else if (type === 'tracking') {
          url = `${API_BASE_URL}/api/tracking/${id}/timeline`;
        } else if (type === 'scene') {
          url = `${API_BASE_URL}/api/scene/timeline?limit=50`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch timeline');

        const data = await response.json();
        setTimeline(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [id, type]);

  const renderPersonTimeline = () => {
    if (!timeline?.person) return null;

    const allEvents = [];

    // Add sessions
    timeline.sessions?.forEach(session => {
      allEvents.push({
        type: 'session',
        timestamp: new Date(session.start),
        data: session
      });
    });

    // Add detections
    timeline.recent_detections?.forEach(detection => {
      allEvents.push({
        type: 'detection',
        timestamp: new Date(detection.timestamp),
        data: detection
      });
    });

    // Add analyses
    timeline.analyses?.forEach(analysis => {
      allEvents.push({
        type: 'analysis',
        timestamp: new Date(analysis.timestamp),
        data: analysis
      });
    });

    // Add observations
    timeline.observations?.forEach(observation => {
      allEvents.push({
        type: 'observation',
        timestamp: new Date(observation.timestamp),
        data: observation
      });
    });

    // Sort by timestamp
    allEvents.sort((a, b) => b.timestamp - a.timestamp);

    // Filter events
    const filteredEvents = filter === 'all'
      ? allEvents
      : allEvents.filter(e => e.type === filter || (filter === 'detections' && e.type === 'detection'));

    return (
      <>
        <div className={styles.personInfo}>
          <h3 className={styles.personName}>{timeline.person.name}</h3>
          <div className={styles.personStats}>
            <span>First Seen: {timeline.person.first_seen ? new Date(timeline.person.first_seen).toLocaleString() : 'N/A'}</span>
            <span>Last Seen: {timeline.person.last_seen ? new Date(timeline.person.last_seen).toLocaleString() : 'N/A'}</span>
            <span>Total Visits: {timeline.person.visit_count}</span>
          </div>
        </div>

        <div className={styles.filterBar}>
          <button
            className={`${styles.filterButton} ${filter === 'all' ? styles.active : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({allEvents.length})
          </button>
          <button
            className={`${styles.filterButton} ${filter === 'detections' ? styles.active : ''}`}
            onClick={() => setFilter('detections')}
          >
            Detections ({timeline.recent_detections?.length || 0})
          </button>
          <button
            className={`${styles.filterButton} ${filter === 'analyses' ? styles.active : ''}`}
            onClick={() => setFilter('analyses')}
          >
            Analyses ({timeline.analyses?.length || 0})
          </button>
          <button
            className={`${styles.filterButton} ${filter === 'observations' ? styles.active : ''}`}
            onClick={() => setFilter('observations')}
          >
            Observations ({timeline.observations?.length || 0})
          </button>
        </div>

        <div className={styles.timelineEvents}>
          {filteredEvents.map((event, index) => (
            <div key={index} className={styles.timelineEvent}>
              <div className={styles.eventTime}>
                {event.timestamp.toLocaleString()}
              </div>
              <div className={`${styles.eventContent} ${styles[event.type]}`}>
                {renderEvent(event)}
              </div>
            </div>
          ))}
        </div>
      </>
    );
  };

  const renderEvent = (event) => {
    switch (event.type) {
      case 'session':
        return (
          <>
            <div className={styles.eventType}>Session</div>
            <div className={styles.eventDetails}>
              <span>Tracking ID: {event.data.tracking_id}</span>
              <span>Detections: {event.data.total_detections}</span>
              <span>Zones: {event.data.zones_visited?.join(', ') || 'None'}</span>
              <span>Status: {event.data.is_active ? 'Active' : 'Ended'}</span>
            </div>
          </>
        );

      case 'detection':
        return (
          <>
            <div className={styles.eventType}>Detection</div>
            <div className={styles.eventDetails}>
              <span>Tracking ID: {event.data.tracking_id}</span>
              <span>Confidence: {(event.data.confidence * 100).toFixed(1)}%</span>
              <span>Zone: {event.data.zone_id || 'Unknown'}</span>
            </div>
          </>
        );

      case 'analysis':
        return (
          <>
            <div className={styles.eventType}>AI Analysis - {event.data.type}</div>
            <div className={styles.eventText}>{event.data.text}</div>
            {event.data.structured_data && (
              <pre className={styles.structuredData}>
                {JSON.stringify(event.data.structured_data, null, 2)}
              </pre>
            )}
          </>
        );

      case 'observation':
        return (
          <>
            <div className={styles.eventType}>
              Manual Observation - {event.data.type}
              {event.data.severity && (
                <span className={`${styles.severity} ${styles[event.data.severity]}`}>
                  {event.data.severity}
                </span>
              )}
            </div>
            {event.data.title && <div className={styles.observationTitle}>{event.data.title}</div>}
            <div className={styles.eventText}>{event.data.description}</div>
            <div className={styles.eventMeta}>
              Recorded by: {event.data.recorded_by}
            </div>
          </>
        );

      default:
        return null;
    }
  };

  const renderSceneTimeline = () => {
    if (!timeline?.timeline) return null;

    return (
      <div className={styles.sceneTimeline}>
        {timeline.timeline.map((scene, index) => (
          <div key={index} className={styles.sceneCard}>
            <div className={styles.sceneHeader}>
              <span className={styles.sceneTime}>
                {new Date(scene.timestamp).toLocaleString()}
              </span>
              <span className={styles.sceneId}>Scene #{scene.scene_id}</span>
            </div>

            <div className={styles.sceneMetrics}>
              <span>Crowd Density: {scene.scene.crowd_density}</span>
              <span>Energy Level: {scene.scene.energy_level}</span>
            </div>

            <div className={styles.sceneSummary}>
              {scene.scene.summary}
            </div>

            {scene.scene.dominant_activities && scene.scene.dominant_activities.length > 0 && (
              <div className={styles.activities}>
                <strong>Activities:</strong> {scene.scene.dominant_activities.join(', ')}
              </div>
            )}

            {scene.events && scene.events.length > 0 && (
              <div className={styles.sceneEvents}>
                <strong>Events:</strong>
                {scene.events.map((event, idx) => (
                  <div key={idx} className={`${styles.sceneEvent} ${styles[event.severity]}`}>
                    <div className={styles.eventHeader}>
                      <span className={styles.eventType}>{event.type}</span>
                      <span className={styles.eventSeverity}>{event.severity}</span>
                    </div>
                    <div className={styles.eventDescription}>{event.description}</div>
                    {event.location && <div className={styles.eventLocation}>Location: {event.location}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className={styles.modal} onClick={onClose}>
        <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
          <div className={styles.loading}>Loading timeline...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.modal} onClick={onClose}>
        <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
          <div className={styles.error}>Error: {error}</div>
          <button onClick={onClose} className={styles.closeButton}>Close</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.modal} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>
            {type === 'person' ? 'Person Timeline' :
             type === 'tracking' ? 'Tracking Timeline' :
             'Scene Timeline'}
          </h2>
          <button onClick={onClose} className={styles.closeButton}>×</button>
        </div>

        <div className={styles.content}>
          {type === 'scene' ? renderSceneTimeline() : renderPersonTimeline()}
        </div>
      </div>
    </div>
  );
}

export default TimelineViewer;
