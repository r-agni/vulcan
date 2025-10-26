"""
Merged Logs Database Schema
2 Master Tables: users and camera_room
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, LargeBinary, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Separate database for merged logs
DATABASE_URL = "sqlite:///./merged_logs.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Users(Base):
    """Master User/People Table - Simple person tracking"""
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Identity
    name = Column(String)  # Auto-generated "Person_timestamp" or manual
    face_encoding = Column(LargeBinary, nullable=True)  # Pickled numpy array
    thumbnail_path = Column(String, nullable=True)  # Path to saved face image

    # Visit Tracking
    first_seen = Column(DateTime, default=datetime.utcnow)  # First detection
    last_seen = Column(DateTime, default=datetime.utcnow)  # Most recent detection
    visit_count = Column(Integer, default=1)  # Number of times seen

    # Optional Notes
    notes = Column(Text, nullable=True)  # Manual staff notes


class CameraRoom(Base):
    """Master Camera/Room Analytics Table - Time-series snapshots every 5 seconds"""
    __tablename__ = "camera_room"

    # Primary Key & Timestamp
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Camera Info
    camera_name = Column(String, default="Main Store Camera")
    camera_source = Column(String)  # YouTube URL or device path
    room_name = Column(String, default="Store Floor 1")

    # Zones & Lines Config (snapshot at this time)
    zones = Column(JSON, nullable=True)  # [{id, name, type, polygon, color, capacity}]
    virtual_lines = Column(JSON, nullable=True)  # [{id, name, start, end, direction}]

    # Real-Time Occupancy Metrics
    occupancy = Column(Integer, default=0)  # Total people in frame right now
    peak_today = Column(Integer, default=0)  # Peak occupancy so far today
    avg_dwell_time = Column(Float, default=0.0)  # Average dwell time in seconds
    active_trajectories = Column(Integer, default=0)  # Number of active movement paths
    total_entries = Column(Integer, default=0)  # Total entries counted today
    active_zones = Column(Integer, default=0)  # Number of zones being monitored

    # Detection Data (at this timestamp)
    detected_person_ids = Column(JSON, nullable=True)  # [person_ids] in frame
    detected_tracking_ids = Column(JSON, nullable=True)  # [tracking_ids] currently active
    detection_count = Column(Integer, default=0)  # Number of people detected
    face_detection_count = Column(Integer, default=0)  # Number of faces recognized
    unknown_person_count = Column(Integer, default=0)  # Detections without face match

    # Tracking Data (active at this timestamp)
    active_sessions = Column(JSON, nullable=True)  # [{tracking_id, person_id, zones_visited}]
    session_count = Column(Integer, default=0)  # Number of active sessions

    # Per-Zone Analytics (snapshot)
    zone_occupancy = Column(JSON, nullable=True)  # {zone_id: person_count}
    zone_dwell_times = Column(JSON, nullable=True)  # {zone_id: avg_dwell_seconds}

    # Movement/Trajectory Data
    trajectories = Column(JSON, nullable=True)  # [{tracking_id, path: [{x,y,time,zone}]}]
    trajectory_count = Column(Integer, default=0)  # Number of active paths

    # Line Crossing Stats
    line_crossings_in = Column(Integer, default=0)  # Total "in" crossings today
    line_crossings_out = Column(Integer, default=0)  # Total "out" crossings today
    recent_crossings = Column(JSON, nullable=True)  # [{line_id, direction, tracking_id, time}]

    # Dwell Time Stats (at this timestamp)
    current_dwell_events = Column(JSON, nullable=True)  # [{tracking_id, zone_id, duration}]
    max_dwell_time_current = Column(Float, nullable=True)  # Longest current dwell time
    min_dwell_time_current = Column(Float, nullable=True)  # Shortest current dwell time

    # Queue Analytics (at this timestamp)
    active_queues = Column(JSON, nullable=True)  # [{zone_id, length, people, wait_time}]
    queue_count = Column(Integer, default=0)  # Number of queues detected
    max_queue_length = Column(Integer, nullable=True)  # Longest queue right now

    # Heatmap Data (latest)
    heatmap_path = Column(String, nullable=True)  # Path to most recent heatmap image
    heatmap_intensity = Column(Float, nullable=True)  # Max intensity value

    # Product Interactions (active at this timestamp)
    active_interactions = Column(JSON, nullable=True)  # [{tracking_id, zone_id, type, duration, hand_pos, gesture}]
    interaction_count = Column(Integer, default=0)  # Number of ongoing interactions
    total_interactions_today = Column(Integer, default=0)  # Cumulative interactions today

    # Gaze/Attention Data (active at this timestamp)
    active_gaze_events = Column(JSON, nullable=True)  # [{tracking_id, zone_id, direction, fixation_duration}]
    gaze_fixation_count = Column(Integer, default=0)  # Number of active fixations
    total_gaze_events_today = Column(Integer, default=0)  # Cumulative gaze events today

    # AI Analysis (Gemini - latest at this timestamp)
    gemini_analysis_text = Column(Text, nullable=True)  # Latest AI analysis text
    crowd_density = Column(String, nullable=True)  # 'low', 'medium', 'high'
    energy_level = Column(String, nullable=True)  # 'calm', 'moderate', 'busy', 'hectic'
    dominant_activities = Column(JSON, nullable=True)  # ['browsing', 'examining', 'purchasing']
    scene_summary = Column(Text, nullable=True)  # Overall scene description
    anomalies_detected = Column(JSON, nullable=True)  # [anomaly descriptions]

    # Events & Alerts (active at this timestamp)
    active_events = Column(JSON, nullable=True)  # [{event_type, severity, description, location}]
    active_alerts = Column(JSON, nullable=True)  # [{alert_id, priority, category, message}]
    event_count = Column(Integer, default=0)  # Number of active events
    alert_count = Column(Integer, default=0)  # Number of active alerts
    critical_alert_count = Column(Integer, default=0)  # Number of critical alerts

    # Behavior Analysis (from Gemini structured data)
    individual_behaviors = Column(JSON, nullable=True)  # [{tracking_id, appearance, emotional_state, purchase_intent, engagement}]
    scene_interactions = Column(JSON, nullable=True)  # [{type, participants, location, description}]

    # Daily Counters (cumulative)
    total_detections_today = Column(Integer, default=0)  # All detections today
    total_sessions_today = Column(Integer, default=0)  # All sessions started today
    total_alerts_today = Column(Integer, default=0)  # All alerts generated today
    total_events_today = Column(Integer, default=0)  # All events logged today

    # Hand Gestures Summary (at this timestamp)
    hand_gestures_summary = Column(JSON, nullable=True)  # {pointing: 0, grabbing: 0, holding: 0, open_palm: 0, total: 0}

    # Customer Recognition Summary (at this timestamp)
    customer_recognition_summary = Column(JSON, nullable=True)
    # {total_recognized: 0, vip_customers_present: 0, new_customers: 0, returning_customers: 0, recognition_rate: 0.0}

    # ==================== PRODUCT INVENTORY DATA ====================

    # Product Catalog Snapshot
    product_inventory = Column(JSON, nullable=True)  # [{id, name, category, zone_id, position, status}]
    total_products = Column(Integer, default=0)  # Total tracked products

    # Active Product Interactions (at this timestamp)
    active_product_interactions = Column(JSON, nullable=True)
    # [{tracking_id, product_id, product_name, interaction_type, duration, engagement_score}]
    product_interaction_count = Column(Integer, default=0)  # Number of active product interactions

    # Product Metrics (aggregated per product)
    product_metrics = Column(JSON, nullable=True)
    # {product_id: {views, touches, pickups, avg_engagement_time, purchase_intent_score}}

    # Product-specific counters (cumulative today)
    total_product_views_today = Column(Integer, default=0)  # Total product gazes today
    total_product_touches_today = Column(Integer, default=0)  # Total product touches today
    total_product_pickups_today = Column(Integer, default=0)  # Total product pickups today

    # Top Products (at this timestamp)
    most_viewed_products = Column(JSON, nullable=True)  # [{product_id, product_name, view_count}]
    most_interacted_products = Column(JSON, nullable=True)  # [{product_id, product_name, interaction_count}]


def init_merged_db():
    """Initialize merged logs database tables"""
    Base.metadata.create_all(bind=engine)
    print("Merged logs database initialized: merged_logs.db")


def get_merged_db():
    """Get merged database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
