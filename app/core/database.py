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
    body_tracking_id = Column(String, nullable=True, index=True)  # Link to body tracking
    scene_analysis_id = Column(Integer, nullable=True)  # Link to overall scene analysis
    timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_type = Column(String)  # 'clothing', 'emotion', 'pathway', 'interest'
    analysis_text = Column(Text)
    video_clip_path = Column(String, nullable=True)
    structured_data = Column(JSON, nullable=True)  # Store structured analysis data


# ==================== BODY TRACKING & SCENE ANALYSIS TABLES ====================

class BodyDetectionEvent(Base):
    """Track body detections with unique tracking IDs"""
    __tablename__ = "body_detection_events"

    id = Column(Integer, primary_key=True, index=True)
    body_tracking_id = Column(String, nullable=False, index=True)  # Unique tracking ID
    person_id = Column(Integer, nullable=True, index=True)  # Linked person if face detected
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bbox_left = Column(Float)
    bbox_top = Column(Float)
    bbox_right = Column(Float)
    bbox_bottom = Column(Float)
    confidence = Column(Float)
    zone_id = Column(Integer, nullable=True)
    frame_path = Column(String, nullable=True)


class PersonSession(Base):
    """Track continuous presence of a person (links tracking_id to person_id over time)"""
    __tablename__ = "person_sessions"

    id = Column(Integer, primary_key=True, index=True)
    body_tracking_id = Column(String, nullable=False, index=True)
    person_id = Column(Integer, nullable=True, index=True)
    session_start = Column(DateTime, default=datetime.utcnow)
    session_end = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    total_detections = Column(Integer, default=1)
    zones_visited = Column(JSON, nullable=True)  # List of zone IDs visited
    is_active = Column(Boolean, default=True)


class SceneAnalysis(Base):
    """Overall scene-level analysis from Gemini"""
    __tablename__ = "scene_analyses"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    time_window_start = Column(String)  # e.g., "00:00"
    time_window_end = Column(String)    # e.g., "00:10"
    video_clip_path = Column(String, nullable=True)

    # Scene-level data
    overall_summary = Column(Text)
    crowd_density = Column(String)  # low, medium, high
    energy_level = Column(String)
    dominant_activities = Column(JSON)  # List of activities
    environmental_context = Column(Text, nullable=True)
    anomalies_detected = Column(JSON, nullable=True)

    # Metadata
    gemini_model = Column(String, default="gemini-2.5-flash")
    analysis_duration_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Full structured response
    full_structured_response = Column(JSON, nullable=True)


class EventLog(Base):
    """Individual events detected in video analysis"""
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    scene_analysis_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    video_timestamp = Column(String)  # Timestamp within video clip (e.g., "00:05")

    event_type = Column(String, nullable=False, index=True)  # customer_interaction, queue_formation, etc.
    severity = Column(String, default="normal")  # normal, attention, warning, critical
    description = Column(Text)
    location = Column(String)

    involved_tracking_ids = Column(JSON)  # List of body tracking IDs involved
    requires_action = Column(Boolean, default=False)
    recommended_action = Column(Text, nullable=True)

    # Status tracking
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)


class InteractionLog(Base):
    """Log interactions between customers, staff, and products"""
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    scene_analysis_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    interaction_type = Column(String, nullable=False)  # customer_product, customer_staff, customer_customer
    participants = Column(JSON)  # List of tracking IDs or identifiers
    location = Column(String)
    zone_id = Column(Integer, nullable=True)

    description = Column(Text)
    duration_seconds = Column(Float, nullable=True)
    outcome = Column(String, nullable=True)  # positive, negative, neutral, ongoing

    # For product interactions
    product_names = Column(JSON, nullable=True)
    engagement_score = Column(Float, nullable=True)


class ManualObservation(Base):
    """Manual annotations and observations by staff"""
    __tablename__ = "manual_observations"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Link to entities
    person_id = Column(Integer, nullable=True, index=True)
    body_tracking_id = Column(String, nullable=True, index=True)
    event_id = Column(Integer, nullable=True)  # Link to EventLog
    zone_id = Column(Integer, nullable=True)

    # Observation data
    observation_type = Column(String, nullable=False)  # note, issue, feedback, action_taken
    title = Column(String)
    description = Column(Text, nullable=False)
    severity = Column(String, default="info")  # info, warning, critical

    # Staff info
    recorded_by = Column(String)  # Staff member name/ID

    # Follow-up
    requires_followup = Column(Boolean, default=False)
    followup_completed = Column(Boolean, default=False)
    followup_notes = Column(Text, nullable=True)


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
    person_id = Column(Integer, nullable=True)  # Optional - may be unknown
    body_tracking_id = Column(String, nullable=True, index=True)  # Body tracking ID
    session_id = Column(String, nullable=False)  # Unique visit session UUID
    timestamp = Column(DateTime, default=datetime.utcnow)
    x_position = Column(Float)  # Normalized 0-1
    y_position = Column(Float)  # Normalized 0-1
    zone_id = Column(Integer, nullable=True)  # Current zone


class DwellTimeRecord(Base):
    """Record time spent in zones"""
    __tablename__ = "dwell_time_records"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=True)  # Optional - may be unknown
    body_tracking_id = Column(String, nullable=True, index=True)  # Body tracking ID
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
    person_id = Column(Integer, nullable=True)  # Optional - may be unknown
    body_tracking_id = Column(String, nullable=True, index=True)  # Body tracking ID
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
    person_ids = Column(JSON)  # List of current person IDs (legacy)
    tracking_ids = Column(JSON, nullable=True)  # List of body tracking IDs


class QueueMetrics(Base):
    """Queue analytics data"""
    __tablename__ = "queue_metrics"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, nullable=False)  # Queue zone
    timestamp = Column(DateTime, default=datetime.utcnow)
    queue_length = Column(Integer)
    avg_wait_time_seconds = Column(Float, nullable=True)
    max_wait_time_seconds = Column(Float, nullable=True)
    people_in_queue = Column(JSON)  # List of person IDs (legacy)
    tracking_ids_in_queue = Column(JSON, nullable=True)  # List of body tracking IDs


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
    product_id = Column(Integer, nullable=True, index=True)  # FK to Product (if identified)
    timestamp = Column(DateTime, default=datetime.utcnow)
    interaction_type = Column(String)  # "looked_at", "picked_up", "examined", "reaching", "touching", "putting_back"
    duration_seconds = Column(Float, nullable=True)
    proximity_cm = Column(Float, nullable=True)  # Distance to product
    engagement_score = Column(Float, nullable=True)  # 0-1

    # Phase 2: Hand & Pose Detection
    hand_position = Column(JSON, nullable=True)  # {x, y} normalized coordinates
    gesture_type = Column(String, nullable=True)  # "pointing", "grabbing", "holding", "open_palm"
    interaction_confidence = Column(Float, nullable=True)  # Confidence score
    hand_landmarks = Column(JSON, nullable=True)  # Full hand skeleton data [{x, y, z}, ...]


class AlertLog(Base):
    """Store alert history for analysis and reporting"""
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, nullable=False, index=True)  # Unique alert identifier
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String, nullable=False)  # low, medium, high, critical
    category = Column(String, nullable=False)  # customer_service, queue_management, etc.
    recipient = Column(String, nullable=False)  # salesperson, manager, both
    status = Column(String, default="active")  # active, acknowledged, expired, dismissed

    person_id = Column(Integer, nullable=True)
    zone_id = Column(Integer, nullable=True)
    zone_name = Column(String, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)

    context_data = Column(JSON, nullable=True)  # Additional context


# ==================== STAFF MANAGEMENT TABLES ====================

class StaffMember(Base):
    """Track staff members and their roles"""
    __tablename__ = "staff_members"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "salesperson", "manager", "cashier"
    expertise_zones = Column(JSON)  # List of zone IDs they specialize in
    shift_start = Column(DateTime, nullable=True)
    shift_end = Column(DateTime, nullable=True)
    is_on_duty = Column(Boolean, default=False)
    phone_number = Column(String, nullable=True)
    notification_preferences = Column(JSON)  # WebSocket, SMS, etc.
    created_at = Column(DateTime, default=datetime.utcnow)


class StaffLocation(Base):
    """Track staff real-time locations"""
    __tablename__ = "staff_locations"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    x_position = Column(Float)  # Normalized 0-1
    y_position = Column(Float)  # Normalized 0-1
    zone_id = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=True)  # Available for assignments
    current_task = Column(String, nullable=True)  # Description of current activity


class AlertAssignment(Base):
    """Track alert assignments to staff"""
    __tablename__ = "alert_assignments"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, nullable=False, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    response_time_seconds = Column(Float, nullable=True)
    completion_time_seconds = Column(Float, nullable=True)
    outcome = Column(String, nullable=True)  # "success", "ignored", "escalated"
    staff_notes = Column(Text, nullable=True)
    customer_satisfaction_score = Column(Integer, nullable=True)  # 1-5


class StaffPerformanceMetrics(Base):
    """Track staff performance for learning"""
    __tablename__ = "staff_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)

    # Alert metrics
    alerts_assigned = Column(Integer, default=0)
    alerts_completed = Column(Integer, default=0)
    alerts_ignored = Column(Integer, default=0)
    avg_response_time_seconds = Column(Float)
    avg_completion_time_seconds = Column(Float)

    # Category expertise (learned over time)
    customer_service_score = Column(Float)  # 0-1
    queue_management_score = Column(Float)
    technical_support_score = Column(Float)

    # Zone coverage
    zones_covered = Column(JSON)  # List of zone IDs worked
    preferred_zones = Column(JSON)  # Learned preferences


# ==================== CUSTOMER RECOGNITION TABLES ====================

class CustomerProfile(Base):
    """Anonymized customer profile for returning customers"""
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    profile_uuid = Column(String, unique=True, nullable=False, index=True)

    # Appearance embedding for re-identification
    appearance_embedding = Column(LargeBinary)  # Serialized vector
    embedding_updated_at = Column(DateTime, default=datetime.utcnow)

    # Visit history
    first_visit = Column(DateTime, default=datetime.utcnow)
    last_visit = Column(DateTime, default=datetime.utcnow)
    total_visits = Column(Integer, default=1)
    visit_frequency = Column(String, nullable=True)  # "weekly", "monthly", etc.

    # Behavioral profile
    favorite_zones = Column(JSON)  # List of zone IDs with frequency
    avg_visit_duration_minutes = Column(Float)
    avg_purchase_intent_score = Column(Float)

    # Preferences (learned)
    preferred_product_categories = Column(JSON)
    typical_visit_time = Column(String, nullable=True)  # "weekday_afternoon", etc.

    # Service history
    vip_status = Column(Boolean, default=False)
    total_interactions_logged = Column(Integer, default=0)
    avg_satisfaction_score = Column(Float, nullable=True)

    # Privacy
    consent_given = Column(Boolean, default=False)
    opt_out_date = Column(DateTime, nullable=True)
    data_retention_expires = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomerVisit(Base):
    """Individual visit record"""
    __tablename__ = "customer_visits"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False, index=True)  # FK to CustomerProfile
    visit_date = Column(DateTime, default=datetime.utcnow, index=True)

    # Session tracking
    session_ids = Column(JSON)  # List of session UUIDs from this visit
    tracking_ids = Column(JSON)  # Body tracking IDs

    # Visit details
    entry_time = Column(DateTime)
    exit_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    zones_visited = Column(JSON)

    # Behavior summary
    purchase_intent_score = Column(Float, nullable=True)
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    staff_interactions_count = Column(Integer, default=0)

    # Outcomes
    purchase_made = Column(Boolean, nullable=True)
    satisfaction_score = Column(Integer, nullable=True)  # 1-5
    notes = Column(Text, nullable=True)


class AppearanceMatch(Base):
    """Log of appearance matching results (for debugging/improvement)"""
    __tablename__ = "appearance_matches"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    tracking_id = Column(String, nullable=False)
    matched_profile_id = Column(Integer, nullable=True)
    confidence_score = Column(Float)  # 0-1

    # Match details
    embedding_distance = Column(Float)
    visual_similarity = Column(Float)
    temporal_plausibility = Column(Float)  # Based on last visit time

    # Decision
    match_accepted = Column(Boolean, default=False)
    match_rejected_reason = Column(String, nullable=True)


# ==================== PHASE 3: GAZE DETECTION TABLES ====================

class GazeEvent(Base):
    """Track gaze detection and attention events"""
    __tablename__ = "gaze_events"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=True, index=True)  # Optional - may be unknown
    body_tracking_id = Column(String, nullable=True, index=True)  # Body tracking ID
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Gaze target
    zone_id = Column(Integer, nullable=True)  # Target zone
    target_type = Column(String, nullable=False)  # "zone", "product", "person", "unknown"
    target_position = Column(JSON, nullable=True)  # {x, y} estimated target location

    # Gaze direction
    gaze_direction = Column(JSON, nullable=False)  # {pitch, yaw, roll} in degrees
    head_pose = Column(JSON, nullable=True)  # {pitch, yaw, roll} head orientation

    # Attention metrics
    fixation_duration_seconds = Column(Float, default=0.0)
    confidence_score = Column(Float)  # Detection confidence

    # Eye landmarks (optional detailed data)
    left_eye_landmarks = Column(JSON, nullable=True)
    right_eye_landmarks = Column(JSON, nullable=True)

    # Status
    is_fixation = Column(Boolean, default=False)  # True if fixation (sustained gaze)

    # Product-specific gaze
    product_id = Column(Integer, nullable=True, index=True)  # Target product if identified


# ==================== PRODUCT INVENTORY TABLES ====================

class Product(Base):
    """Product catalog - items tracked in store"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True, index=True)  # "Electronics", "Clothing", etc.
    sku = Column(String, nullable=True, unique=True)  # Product SKU/barcode
    description = Column(Text, nullable=True)

    # Visual identification
    image_path = Column(String, nullable=True)  # Reference product image
    color = Column(String, nullable=True)  # For visualization

    # Pricing (optional)
    price = Column(Float, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # AI-generated metadata
    gemini_description = Column(Text, nullable=True)  # AI-generated product description
    gemini_confidence = Column(Float, nullable=True)  # Confidence in AI identification


class ProductZoneMapping(Base):
    """Maps products to specific locations within zones"""
    __tablename__ = "product_zone_mappings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)  # FK to Product
    zone_id = Column(Integer, nullable=False, index=True)  # FK to Zone

    # Position within zone (normalized 0-1 coordinates)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    bounding_box = Column(JSON, nullable=True)  # {"x1": 0.1, "y1": 0.2, "x2": 0.3, "y2": 0.4}

    # Shelf/display information
    shelf_level = Column(String, nullable=True)  # "top", "middle", "bottom"
    display_section = Column(String, nullable=True)  # Section identifier

    # Metadata
    is_primary_location = Column(Boolean, default=True)  # Primary vs secondary location
    stock_status = Column(String, default="in_stock")  # "in_stock", "low_stock", "out_of_stock"
    last_verified = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)


class ProductInteractionEvent(Base):
    """Extended product interaction tracking with detailed metrics"""
    __tablename__ = "product_interaction_events"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=True, index=True)
    body_tracking_id = Column(String, nullable=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)  # FK to Product
    zone_id = Column(Integer, nullable=False, index=True)  # FK to Zone

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Interaction details
    interaction_type = Column(String, nullable=False, index=True)
    # Types: "gazing", "reaching", "touching", "picking_up", "examining", "putting_back", "comparing"

    duration_seconds = Column(Float, nullable=True)
    engagement_score = Column(Float, nullable=True)  # 0-1 based on interaction quality

    # Hand interaction data
    hand_position = Column(JSON, nullable=True)  # {x, y}
    gesture_type = Column(String, nullable=True)  # "pointing", "grabbing", "holding", "open_palm"
    hand_landmarks = Column(JSON, nullable=True)  # Full hand skeleton

    # Gaze data
    gaze_duration_seconds = Column(Float, nullable=True)
    gaze_confidence = Column(Float, nullable=True)

    # Outcome
    interaction_ended = Column(Boolean, default=False)
    outcome = Column(String, nullable=True)  # "picked_up", "put_back", "ignored", "purchased"

    # Metadata
    confidence_score = Column(Float)  # Overall detection confidence
    notes = Column(Text, nullable=True)


class ProductEngagementMetrics(Base):
    """Aggregated metrics per product for analytics"""
    __tablename__ = "product_engagement_metrics"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, unique=True, index=True)  # FK to Product

    # View metrics
    total_views = Column(Integer, default=0)  # Number of times gazed at
    total_view_duration_seconds = Column(Float, default=0.0)
    avg_view_duration = Column(Float, default=0.0)

    # Touch metrics
    total_touches = Column(Integer, default=0)  # Number of times touched
    total_pickups = Column(Integer, default=0)  # Number of times picked up
    total_putbacks = Column(Integer, default=0)  # Number of times put back

    # Engagement
    total_engagement_time_seconds = Column(Float, default=0.0)
    avg_engagement_score = Column(Float, default=0.0)

    # Conversion
    purchase_intent_score = Column(Float, default=0.0)  # 0-1 likelihood of purchase
    estimated_conversions = Column(Integer, default=0)  # Estimated purchases

    # Temporal data
    last_interaction = Column(DateTime, nullable=True)
    peak_interaction_hour = Column(Integer, nullable=True)  # 0-23

    # Update tracking
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
