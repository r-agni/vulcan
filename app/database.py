from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, LargeBinary, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./video_ai.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Person(Base):
    """Person profile in database"""
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    face_encoding = Column(LargeBinary)  # Store face encoding as binary
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    visit_count = Column(Integer, default=1)
    thumbnail_path = Column(String, nullable=True)
    notes = Column(Text, nullable=True)


class DetectionEvent(Base):
    """Individual detection events"""
    __tablename__ = "detection_events"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=True)  # FK to Person, nullable for unknown
    timestamp = Column(DateTime, default=datetime.utcnow)
    confidence = Column(Float)
    frame_path = Column(String, nullable=True)
    location = Column(String, nullable=True)  # Camera location


class BehaviorAnalysis(Base):
    """AI-generated behavior analysis"""
    __tablename__ = "behavior_analysis"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=True)
    detection_event_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_type = Column(String)  # 'clothing', 'emotion', 'pathway', 'interest'
    analysis_text = Column(Text)
    video_clip_path = Column(String, nullable=True)


# ==================== RETAIL ANALYTICS TABLES ====================

class Zone(Base):
    """Store zones / regions of interest"""
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Electronics", "Checkout", etc.
    zone_type = Column(String, nullable=False)  # "product", "queue", "entrance", "aisle"
    polygon_points = Column(JSON)  # [[x1,y1], [x2,y2], ...] normalized 0-1
    color = Column(String, default="#00FF00")  # Hex color for visualization
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    max_capacity = Column(Integer, nullable=True)  # Optional capacity limit


class PersonTrajectory(Base):
    """Track person movement paths"""
    __tablename__ = "person_trajectories"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=False)
    session_id = Column(String, nullable=False)  # Unique visit session UUID
    timestamp = Column(DateTime, default=datetime.utcnow)
    x_position = Column(Float)  # Normalized 0-1
    y_position = Column(Float)  # Normalized 0-1
    zone_id = Column(Integer, nullable=True)  # Current zone


class DwellTimeRecord(Base):
    """Record time spent in zones"""
    __tablename__ = "dwell_time_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=False)
    session_id = Column(String, nullable=False)
    zone_id = Column(Integer, nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    engagement_score = Column(Float, nullable=True)  # 0-1 based on attention


class VirtualLine(Base):
    """Virtual lines for entry/exit counting"""
    __tablename__ = "virtual_lines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "Store Entrance", "Checkout Line"
    start_point = Column(JSON)  # {"x": 0.2, "y": 0.5}
    end_point = Column(JSON)  # {"x": 0.8, "y": 0.5}
    count_direction = Column(String, default="both")  # "both", "in", "out"
    color = Column(String, default="#FF0000")
    is_active = Column(Boolean, default=True)


class LineCrossingEvent(Base):
    """Record line crossing events"""
    __tablename__ = "line_crossing_events"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=True)
    line_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    direction = Column(String)  # "in" or "out"
    crossing_point = Column(JSON)  # {"x": 0.5, "y": 0.3}


class OccupancyLog(Base):
    """Log occupancy counts over time"""
    __tablename__ = "occupancy_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    zone_id = Column(Integer, nullable=True)  # NULL = entire store
    person_count = Column(Integer)
    person_ids = Column(JSON)  # List of current person IDs


class QueueMetrics(Base):
    """Queue analytics data"""
    __tablename__ = "queue_metrics"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, nullable=False)  # Queue zone
    timestamp = Column(DateTime, default=datetime.utcnow)
    queue_length = Column(Integer)
    avg_wait_time_seconds = Column(Float, nullable=True)
    max_wait_time_seconds = Column(Float, nullable=True)
    people_in_queue = Column(JSON)  # List of person IDs


class HeatmapData(Base):
    """Store heatmap data for visualization"""
    __tablename__ = "heatmap_data"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    time_bucket = Column(String)  # "2025-10-18_14:00" (hourly bucket)
    heatmap_array = Column(LargeBinary)  # Serialized numpy array
    max_intensity = Column(Float)
    image_path = Column(String, nullable=True)  # Generated heatmap image


class ProductInteraction(Base):
    """Track product/display interactions"""
    __tablename__ = "product_interactions"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=False)
    zone_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    interaction_type = Column(String)  # "looked_at", "picked_up", "examined"
    duration_seconds = Column(Float, nullable=True)
    proximity_cm = Column(Float, nullable=True)  # Distance to product
    engagement_score = Column(Float, nullable=True)  # 0-1


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
