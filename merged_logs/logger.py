"""
Merged Logger Service
Handles saving data to the merged_logs database
"""

from datetime import datetime
from typing import Dict, Any, Optional, Callable
import pickle
from sqlalchemy.orm import Session
import threading
import queue

from .database import Users, CameraRoom, SessionLocal


class MergedLogger:
    """Service for logging to merged_logs database"""

    def __init__(self):
        self.db_session: Optional[Session] = None
        self.rag_indexing_callback: Optional[Callable] = None
        self.indexing_queue: queue.Queue = queue.Queue(maxsize=100)
        self.indexing_enabled: bool = False

    def get_session(self) -> Session:
        """Get or create database session"""
        if self.db_session is None:
            self.db_session = SessionLocal()
        return self.db_session

    def close_session(self):
        """Close database session"""
        if self.db_session:
            self.db_session.close()
            self.db_session = None

    def enable_rag_indexing(self, callback: Optional[Callable] = None):
        """
        Enable automatic RAG indexing after each snapshot save

        Args:
            callback: Optional callback function to call for indexing.
                     If None, will trigger incremental indexing via queue.
        """
        self.indexing_enabled = True
        self.rag_indexing_callback = callback
        print("✓ RAG auto-indexing enabled")

    def disable_rag_indexing(self):
        """Disable automatic RAG indexing"""
        self.indexing_enabled = False
        print("✗ RAG auto-indexing disabled")

    def _trigger_rag_indexing(self, snapshot_id: int):
        """
        Trigger RAG indexing for a new snapshot (non-blocking)

        Args:
            snapshot_id: ID of the camera_room record to index
        """
        if not self.indexing_enabled:
            return

        try:
            # Add to queue for background indexing
            if not self.indexing_queue.full():
                self.indexing_queue.put(snapshot_id, block=False)

            # Call callback if provided
            if self.rag_indexing_callback:
                # Run callback in background thread to avoid blocking
                thread = threading.Thread(
                    target=self.rag_indexing_callback,
                    args=(snapshot_id,),
                    daemon=True
                )
                thread.start()
        except Exception as e:
            print(f"Warning: RAG indexing trigger failed: {e}")

    def save_camera_snapshot(self, snapshot_data: Dict[str, Any]) -> Optional[CameraRoom]:
        """
        Save a camera_room snapshot to database
        Called every 5 seconds synchronized with Gemini analysis

        Args:
            snapshot_data: Dictionary from collect_analytics_snapshot()

        Returns:
            CameraRoom record or None if error
        """
        try:
            db = self.get_session()

            # Create CameraRoom record
            camera_record = CameraRoom(
                timestamp=snapshot_data.get('timestamp', datetime.utcnow()),

                # Camera Info
                camera_name=snapshot_data.get('camera_name', 'Main Store Camera'),
                camera_source=snapshot_data.get('camera_source', ''),
                room_name=snapshot_data.get('room_name', 'Store Floor 1'),

                # Zones & Lines
                zones=snapshot_data.get('zones'),
                virtual_lines=snapshot_data.get('virtual_lines'),

                # Real-Time Metrics
                occupancy=snapshot_data.get('occupancy', 0),
                peak_today=snapshot_data.get('peak_today', 0),
                avg_dwell_time=snapshot_data.get('avg_dwell_time', 0.0),
                active_trajectories=snapshot_data.get('active_trajectories', 0),
                total_entries=snapshot_data.get('total_entries', 0),
                active_zones=snapshot_data.get('active_zones', 0),

                # Detection Data
                detected_person_ids=snapshot_data.get('detected_person_ids'),
                detected_tracking_ids=snapshot_data.get('detected_tracking_ids'),
                detection_count=snapshot_data.get('detection_count', 0),
                face_detection_count=snapshot_data.get('face_detection_count', 0),
                unknown_person_count=snapshot_data.get('unknown_person_count', 0),

                # Tracking Data
                active_sessions=snapshot_data.get('active_sessions'),
                session_count=snapshot_data.get('session_count', 0),

                # Zone Analytics
                zone_occupancy=snapshot_data.get('zone_occupancy'),
                zone_dwell_times=snapshot_data.get('zone_dwell_times'),

                # Trajectories
                trajectories=snapshot_data.get('trajectories'),
                trajectory_count=snapshot_data.get('trajectory_count', 0),

                # Line Crossings
                line_crossings_in=snapshot_data.get('line_crossings_in', 0),
                line_crossings_out=snapshot_data.get('line_crossings_out', 0),
                recent_crossings=snapshot_data.get('recent_crossings'),

                # Dwell Times
                current_dwell_events=snapshot_data.get('current_dwell_events'),
                max_dwell_time_current=snapshot_data.get('max_dwell_time_current'),
                min_dwell_time_current=snapshot_data.get('min_dwell_time_current'),

                # Queues
                active_queues=snapshot_data.get('active_queues'),
                queue_count=snapshot_data.get('queue_count', 0),
                max_queue_length=snapshot_data.get('max_queue_length'),

                # Heatmap
                heatmap_path=snapshot_data.get('heatmap_path'),
                heatmap_intensity=snapshot_data.get('heatmap_intensity'),

                # Interactions
                active_interactions=snapshot_data.get('active_interactions'),
                interaction_count=snapshot_data.get('interaction_count', 0),
                total_interactions_today=snapshot_data.get('total_interactions_today', 0),

                # Gaze
                active_gaze_events=snapshot_data.get('active_gaze_events'),
                gaze_fixation_count=snapshot_data.get('gaze_fixation_count', 0),
                total_gaze_events_today=snapshot_data.get('total_gaze_events_today', 0),

                # AI Analysis
                gemini_analysis_text=snapshot_data.get('gemini_analysis_text'),
                crowd_density=snapshot_data.get('crowd_density'),
                energy_level=snapshot_data.get('energy_level'),
                dominant_activities=snapshot_data.get('dominant_activities'),
                scene_summary=snapshot_data.get('scene_summary'),
                anomalies_detected=snapshot_data.get('anomalies_detected'),

                # Events & Alerts
                active_events=snapshot_data.get('active_events'),
                active_alerts=snapshot_data.get('active_alerts'),
                event_count=snapshot_data.get('event_count', 0),
                alert_count=snapshot_data.get('alert_count', 0),
                critical_alert_count=snapshot_data.get('critical_alert_count', 0),

                # Behavior Analysis
                individual_behaviors=snapshot_data.get('individual_behaviors'),
                scene_interactions=snapshot_data.get('scene_interactions'),

                # Daily Counters
                total_detections_today=snapshot_data.get('total_detections_today', 0),
                total_sessions_today=snapshot_data.get('total_sessions_today', 0),
                total_alerts_today=snapshot_data.get('total_alerts_today', 0),
                total_events_today=snapshot_data.get('total_events_today', 0)
            )

            db.add(camera_record)
            db.commit()
            db.refresh(camera_record)

            # Trigger RAG indexing for this snapshot
            self._trigger_rag_indexing(camera_record.id)

            return camera_record

        except Exception as e:
            print(f"Error saving camera snapshot: {e}")
            if db:
                db.rollback()
            return None

    def create_or_update_user(
        self,
        person_id: int,
        name: str,
        face_encoding: bytes = None,
        thumbnail_path: str = None,
        notes: str = None
    ) -> Optional[Users]:
        """
        Create new user or update existing user

        Args:
            person_id: Person ID from original database
            name: Person name
            face_encoding: Pickled face encoding bytes
            thumbnail_path: Path to thumbnail image
            notes: Optional notes

        Returns:
            Users record or None if error
        """
        try:
            db = self.get_session()

            # Check if user already exists
            user = db.query(Users).filter(Users.id == person_id).first()

            if user:
                # Update existing user
                user.last_seen = datetime.utcnow()
                user.visit_count += 1

                # Update fields if provided
                if name:
                    user.name = name
                if face_encoding:
                    user.face_encoding = face_encoding
                if thumbnail_path:
                    user.thumbnail_path = thumbnail_path
                if notes:
                    user.notes = notes

            else:
                # Create new user
                user = Users(
                    id=person_id,
                    name=name,
                    face_encoding=face_encoding,
                    thumbnail_path=thumbnail_path,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    visit_count=1,
                    notes=notes
                )
                db.add(user)

            db.commit()
            db.refresh(user)

            return user

        except Exception as e:
            print(f"Error creating/updating user: {e}")
            if db:
                db.rollback()
            return None

    def update_user_last_seen(self, person_id: int) -> bool:
        """
        Update user's last_seen timestamp and increment visit_count

        Args:
            person_id: Person ID from original database

        Returns:
            True if successful, False otherwise
        """
        try:
            db = self.get_session()

            user = db.query(Users).filter(Users.id == person_id).first()
            if user:
                user.last_seen = datetime.utcnow()
                user.visit_count += 1
                db.commit()
                return True

            return False

        except Exception as e:
            print(f"Error updating user last seen: {e}")
            if db:
                db.rollback()
            return False

    def get_user(self, person_id: int) -> Optional[Users]:
        """Get user by person_id"""
        try:
            db = self.get_session()
            return db.query(Users).filter(Users.id == person_id).first()
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def get_latest_camera_snapshot(self) -> Optional[CameraRoom]:
        """Get the most recent camera snapshot"""
        try:
            db = self.get_session()
            return db.query(CameraRoom).order_by(CameraRoom.timestamp.desc()).first()
        except Exception as e:
            print(f"Error getting latest snapshot: {e}")
            return None

    def get_camera_snapshots_range(self, start_time: datetime, end_time: datetime) -> list:
        """Get camera snapshots within a time range"""
        try:
            db = self.get_session()
            return db.query(CameraRoom).filter(
                CameraRoom.timestamp >= start_time,
                CameraRoom.timestamp <= end_time
            ).order_by(CameraRoom.timestamp).all()
        except Exception as e:
            print(f"Error getting snapshot range: {e}")
            return []


# Global logger instance
merged_logger = MergedLogger()
