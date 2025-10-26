"""
Body Tracking System
Assigns persistent tracking IDs to detected bodies across frames
Links tracking IDs to person IDs when faces are detected
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import uuid

try:
    from app.core.database import BodyDetectionEvent, PersonSession
except ImportError:
    from app.core.database import BodyDetectionEvent, PersonSession


class BodyTracker:
    """
    Track bodies across frames using spatial proximity and temporal continuity
    Maintains persistent tracking IDs and links them to person IDs when faces are detected
    """

    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30):
        """
        Initialize body tracker

        Args:
            iou_threshold: Minimum IoU to consider same person
            max_age: Maximum frames a track can be inactive before removal
        """
        self.iou_threshold = iou_threshold
        self.max_age = max_age

        # Active tracks: tracking_id -> track_data
        self.active_tracks: Dict[str, Dict] = {}

        # Track counter for generating IDs
        self.track_counter = 0

        # Mapping: tracking_id -> person_id (when face is detected)
        self.tracking_to_person: Dict[str, Optional[int]] = {}

    def _compute_iou(
        self,
        bbox1: Tuple[int, int, int, int],
        bbox2: Tuple[int, int, int, int]
    ) -> float:
        """
        Compute Intersection over Union (IoU) between two bounding boxes

        Args:
            bbox1, bbox2: (left, top, right, bottom)

        Returns:
            IoU score (0.0 to 1.0)
        """
        # Extract coordinates
        left1, top1, right1, bottom1 = bbox1
        left2, top2, right2, bottom2 = bbox2

        # Compute intersection
        inter_left = max(left1, left2)
        inter_top = max(top1, top2)
        inter_right = min(right1, right2)
        inter_bottom = min(bottom1, bottom2)

        if inter_right <= inter_left or inter_bottom <= inter_top:
            return 0.0

        inter_area = (inter_right - inter_left) * (inter_bottom - inter_top)

        # Compute union
        area1 = (right1 - left1) * (bottom1 - top1)
        area2 = (right2 - left2) * (bottom2 - top2)
        union_area = area1 + area2 - inter_area

        if union_area == 0:
            return 0.0

        return inter_area / union_area

    def _generate_tracking_id(self) -> str:
        """Generate a unique tracking ID"""
        self.track_counter += 1
        return f"track_{self.track_counter:04d}"

    def update(
        self,
        detections: List[Tuple[Tuple[int, int, int, int], float, Optional[int]]],
        timestamp: datetime
    ) -> List[Dict]:
        """
        Update tracker with new detections

        Args:
            detections: List of (bbox, confidence, person_id) tuples
                       bbox is (left, top, right, bottom)
                       person_id is None if no face detected, or person ID if face recognized
            timestamp: Current timestamp

        Returns:
            List of track dictionaries with tracking_id, bbox, person_id, etc.
        """
        # Increment age for all tracks
        for track_id in self.active_tracks:
            self.active_tracks[track_id]['age'] += 1

        # Match detections to existing tracks
        matched_tracks = set()
        matched_detections = set()
        new_tracks = []

        for det_idx, (bbox, confidence, person_id) in enumerate(detections):
            best_match_id = None
            best_iou = 0.0

            # Find best matching track
            for track_id, track_data in self.active_tracks.items():
                if track_id in matched_tracks:
                    continue

                iou = self._compute_iou(bbox, track_data['bbox'])

                if iou > self.iou_threshold and iou > best_iou:
                    best_iou = iou
                    best_match_id = track_id

            if best_match_id:
                # Update existing track
                self.active_tracks[best_match_id]['bbox'] = bbox
                self.active_tracks[best_match_id]['confidence'] = confidence
                self.active_tracks[best_match_id]['last_seen'] = timestamp
                self.active_tracks[best_match_id]['age'] = 0
                self.active_tracks[best_match_id]['total_detections'] += 1

                # Link to person_id if face detected
                if person_id is not None:
                    self.active_tracks[best_match_id]['person_id'] = person_id
                    self.tracking_to_person[best_match_id] = person_id

                matched_tracks.add(best_match_id)
                matched_detections.add(det_idx)

                new_tracks.append({
                    'tracking_id': best_match_id,
                    'bbox': bbox,
                    'confidence': confidence,
                    'person_id': self.active_tracks[best_match_id].get('person_id'),
                    'is_new': False
                })
            else:
                # Create new track
                tracking_id = self._generate_tracking_id()

                self.active_tracks[tracking_id] = {
                    'tracking_id': tracking_id,
                    'bbox': bbox,
                    'confidence': confidence,
                    'person_id': person_id,
                    'first_seen': timestamp,
                    'last_seen': timestamp,
                    'age': 0,
                    'total_detections': 1
                }

                if person_id is not None:
                    self.tracking_to_person[tracking_id] = person_id

                matched_detections.add(det_idx)

                new_tracks.append({
                    'tracking_id': tracking_id,
                    'bbox': bbox,
                    'confidence': confidence,
                    'person_id': person_id,
                    'is_new': True
                })

        # Remove old tracks
        tracks_to_remove = []
        for track_id, track_data in self.active_tracks.items():
            if track_data['age'] > self.max_age:
                tracks_to_remove.append(track_id)

        for track_id in tracks_to_remove:
            del self.active_tracks[track_id]
            if track_id in self.tracking_to_person:
                del self.tracking_to_person[track_id]

        return new_tracks

    def get_person_id(self, tracking_id: str) -> Optional[int]:
        """Get person_id associated with a tracking_id"""
        return self.tracking_to_person.get(tracking_id)

    def link_tracking_to_person(self, tracking_id: str, person_id: int):
        """Manually link a tracking_id to a person_id"""
        if tracking_id in self.active_tracks:
            self.active_tracks[tracking_id]['person_id'] = person_id
            self.tracking_to_person[tracking_id] = person_id

    def get_active_tracks(self) -> Dict[str, Dict]:
        """Get all currently active tracks"""
        return self.active_tracks.copy()

    def log_detection_to_db(
        self,
        db: Session,
        tracking_id: str,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        person_id: Optional[int],
        zone_id: Optional[int],
        frame_path: Optional[str] = None
    ) -> BodyDetectionEvent:
        """
        Log a body detection event to the database

        Args:
            db: Database session
            tracking_id: Tracking ID
            bbox: Bounding box (left, top, right, bottom)
            confidence: Detection confidence
            person_id: Associated person ID (if known)
            zone_id: Zone ID where detection occurred
            frame_path: Path to saved frame

        Returns:
            BodyDetectionEvent record
        """
        left, top, right, bottom = bbox

        event = BodyDetectionEvent(
            body_tracking_id=tracking_id,
            person_id=person_id,
            bbox_left=left,
            bbox_top=top,
            bbox_right=right,
            bbox_bottom=bottom,
            confidence=confidence,
            zone_id=zone_id,
            frame_path=frame_path,
            timestamp=datetime.utcnow()
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return event

    def update_or_create_session(
        self,
        db: Session,
        tracking_id: str,
        person_id: Optional[int],
        zone_id: Optional[int]
    ) -> PersonSession:
        """
        Update or create a person session

        Args:
            db: Database session
            tracking_id: Tracking ID
            person_id: Associated person ID (if known)
            zone_id: Current zone ID

        Returns:
            PersonSession record
        """
        # Check if active session exists
        session = db.query(PersonSession).filter(
            PersonSession.body_tracking_id == tracking_id,
            PersonSession.is_active == True
        ).first()

        if session:
            # Update existing session
            session.last_seen = datetime.utcnow()
            session.total_detections += 1

            # Update person_id if newly detected
            if person_id is not None and session.person_id is None:
                session.person_id = person_id

            # Update zones visited
            if zone_id is not None:
                zones_visited = session.zones_visited or []
                if zone_id not in zones_visited:
                    zones_visited.append(zone_id)
                    session.zones_visited = zones_visited

            db.commit()
            db.refresh(session)
        else:
            # Create new session
            session = PersonSession(
                body_tracking_id=tracking_id,
                person_id=person_id,
                session_start=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                total_detections=1,
                zones_visited=[zone_id] if zone_id else [],
                is_active=True
            )

            db.add(session)
            db.commit()
            db.refresh(session)

        return session

    def end_session(self, db: Session, tracking_id: str):
        """
        End a person session (mark as inactive)

        Args:
            db: Database session
            tracking_id: Tracking ID
        """
        session = db.query(PersonSession).filter(
            PersonSession.body_tracking_id == tracking_id,
            PersonSession.is_active == True
        ).first()

        if session:
            session.is_active = False
            session.session_end = datetime.utcnow()
            db.commit()

    def get_all_tracked_bodies(self) -> List[Dict]:
        """
        Get information about all currently tracked bodies

        Returns:
            List of dictionaries with tracking info
        """
        result = []
        for tracking_id, track_data in self.active_tracks.items():
            result.append({
                'tracking_id': tracking_id,
                'person_id': track_data.get('person_id'),
                'bbox': track_data['bbox'],
                'confidence': track_data['confidence'],
                'first_seen': track_data['first_seen'],
                'last_seen': track_data['last_seen'],
                'total_detections': track_data['total_detections'],
                'age': track_data['age']
            })
        return result

    def get_summary_stats(self) -> Dict:
        """Get summary statistics"""
        total_tracks = len(self.active_tracks)
        tracks_with_person_id = sum(
            1 for track in self.active_tracks.values()
            if track.get('person_id') is not None
        )
        tracks_without_person_id = total_tracks - tracks_with_person_id

        return {
            'total_active_tracks': total_tracks,
            'identified_tracks': tracks_with_person_id,
            'unidentified_tracks': tracks_without_person_id,
            'total_tracks_created': self.track_counter
        }
