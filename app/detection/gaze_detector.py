"""
Gaze Detection & Direction Analysis
Detects face landmarks and estimates gaze direction using MediaPipe Face Mesh
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, List, Tuple, Optional
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from dataclasses import dataclass
import math

try:
    from app.core.database import GazeEvent
except ImportError:
    from app.core.database import GazeEvent


@dataclass
class GazeData:
    """Data class for gaze detection results"""
    person_bbox: Tuple[int, int, int, int]  # (left, top, right, bottom)
    gaze_direction: Tuple[float, float, float]  # (pitch, yaw, roll) in degrees
    head_pose: Tuple[float, float, float]  # (pitch, yaw, roll) head orientation
    left_eye_center: Tuple[float, float]  # Normalized coordinates
    right_eye_center: Tuple[float, float]  # Normalized coordinates
    confidence: float
    face_landmarks: np.ndarray  # 468 landmarks
    target_position: Optional[Tuple[float, float]] = None  # Estimated gaze target


@dataclass
class GazeFixation:
    """Data class for gaze fixation tracking"""
    tracking_id: str
    person_id: Optional[int]
    zone_id: Optional[int]
    target_type: str  # "zone", "product", "person", "unknown"
    gaze_direction: Tuple[float, float, float]
    fixation_start: datetime
    last_update: datetime
    confidence: float


class GazeDetector:
    """
    Detect face landmarks and estimate gaze direction using MediaPipe Face Mesh
    """

    # Face mesh landmark indices for key features
    LEFT_EYE_INDICES = [33, 133, 160, 159, 158, 157, 173, 144]  # Left eye contour
    RIGHT_EYE_INDICES = [362, 263, 387, 386, 385, 384, 398, 373]  # Right eye contour
    LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]  # Left iris
    RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]  # Right iris
    NOSE_TIP_INDEX = 1
    CHIN_INDEX = 152
    LEFT_EYE_CORNER = 33
    RIGHT_EYE_CORNER = 263

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        fixation_threshold_seconds: float = 0.5,  # Minimum time to consider fixation
        gaze_stability_threshold: float = 15.0  # Degrees - max change to maintain fixation
    ):
        """
        Initialize gaze detector

        Args:
            min_detection_confidence: Minimum confidence for face detection
            min_tracking_confidence: Minimum confidence for face tracking
            fixation_threshold_seconds: Minimum duration to consider gaze fixation
            gaze_stability_threshold: Maximum gaze direction change to maintain fixation
        """
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=4,  # Track up to 4 faces
            refine_landmarks=True,  # Enable iris tracking
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.fixation_threshold = fixation_threshold_seconds
        self.gaze_stability_threshold = gaze_stability_threshold

        # Active fixations: tracking_id -> GazeFixation
        self.active_fixations: Dict[str, GazeFixation] = {}

    def detect_face_and_gaze(
        self,
        frame: np.ndarray,
        person_bbox: Tuple[int, int, int, int]
    ) -> Optional[GazeData]:
        """
        Detect face landmarks and estimate gaze direction

        Args:
            frame: Input BGR frame
            person_bbox: Person bounding box (left, top, right, bottom)

        Returns:
            GazeData object or None if no face detected
        """
        left, top, right, bottom = person_bbox
        frame_height, frame_width = frame.shape[:2]

        # Crop to person bbox
        person_crop = frame[top:bottom, left:right]

        if person_crop.size == 0:
            return None

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)

        # Process frame
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return None

        # Use first detected face
        face_landmarks = results.multi_face_landmarks[0]

        # Convert landmarks to numpy array
        landmarks = np.array([
            [lm.x, lm.y, lm.z]
            for lm in face_landmarks.landmark
        ])

        # Estimate head pose and gaze direction
        head_pose = self._estimate_head_pose(landmarks)
        gaze_direction = self._estimate_gaze_direction(landmarks, head_pose)

        # Calculate eye centers
        left_eye_center = self._calculate_eye_center(landmarks, self.LEFT_EYE_INDICES)
        right_eye_center = self._calculate_eye_center(landmarks, self.RIGHT_EYE_INDICES)

        # Convert eye centers to full frame coordinates
        crop_width = right - left
        crop_height = bottom - top

        left_eye_full = (
            (left + left_eye_center[0] * crop_width) / frame_width,
            (top + left_eye_center[1] * crop_height) / frame_height
        )
        right_eye_full = (
            (left + right_eye_center[0] * crop_width) / frame_width,
            (top + right_eye_center[1] * crop_height) / frame_height
        )

        # Estimate gaze target position in frame
        target_position = self._project_gaze_to_plane(
            left_eye_full,
            right_eye_full,
            gaze_direction
        )

        # Calculate confidence (based on face detection quality)
        confidence = self._calculate_confidence(landmarks)

        gaze_data = GazeData(
            person_bbox=person_bbox,
            gaze_direction=gaze_direction,
            head_pose=head_pose,
            left_eye_center=left_eye_full,
            right_eye_center=right_eye_full,
            confidence=confidence,
            face_landmarks=landmarks,
            target_position=target_position
        )

        return gaze_data

    def _estimate_head_pose(
        self,
        landmarks: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Estimate head pose (pitch, yaw, roll) from face landmarks

        Args:
            landmarks: Face landmarks array

        Returns:
            (pitch, yaw, roll) in degrees
        """
        # Use key facial landmarks for head pose estimation
        nose_tip = landmarks[self.NOSE_TIP_INDEX]
        chin = landmarks[self.CHIN_INDEX]
        left_eye = landmarks[self.LEFT_EYE_CORNER]
        right_eye = landmarks[self.RIGHT_EYE_CORNER]

        # Calculate pitch (up/down tilt)
        # Positive pitch = looking up, negative = looking down
        vertical_ratio = (nose_tip[1] - chin[1])
        pitch = -np.arctan2(vertical_ratio, 0.1) * 180 / np.pi
        pitch = np.clip(pitch, -90, 90)

        # Calculate yaw (left/right rotation)
        # Positive yaw = looking right, negative = looking left
        eye_center_x = (left_eye[0] + right_eye[0]) / 2
        horizontal_offset = nose_tip[0] - eye_center_x
        yaw = np.arctan2(horizontal_offset, 0.1) * 180 / np.pi
        yaw = np.clip(yaw, -90, 90)

        # Calculate roll (head tilt)
        # Positive roll = tilted clockwise
        eye_slope = (right_eye[1] - left_eye[1]) / (right_eye[0] - left_eye[0] + 1e-6)
        roll = np.arctan(eye_slope) * 180 / np.pi
        roll = np.clip(roll, -45, 45)

        return (pitch, yaw, roll)

    def _estimate_gaze_direction(
        self,
        landmarks: np.ndarray,
        head_pose: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        Estimate gaze direction from eye iris position

        Args:
            landmarks: Face landmarks array
            head_pose: (pitch, yaw, roll) head orientation

        Returns:
            (pitch, yaw, roll) gaze direction in degrees
        """
        pitch_head, yaw_head, roll_head = head_pose

        # Get iris centers if available (landmarks 468-477)
        if len(landmarks) > 477:
            left_iris = landmarks[self.LEFT_IRIS_INDICES]
            right_iris = landmarks[self.RIGHT_IRIS_INDICES]

            left_iris_center = np.mean(left_iris, axis=0)
            right_iris_center = np.mean(right_iris, axis=0)

            # Get eye bounds
            left_eye_landmarks = landmarks[self.LEFT_EYE_INDICES]
            right_eye_landmarks = landmarks[self.RIGHT_EYE_INDICES]

            left_eye_center = np.mean(left_eye_landmarks, axis=0)
            right_eye_center = np.mean(right_eye_landmarks, axis=0)

            # Calculate gaze offset from eye center
            left_offset = left_iris_center - left_eye_center
            right_offset = right_iris_center - right_eye_center

            # Average offset
            avg_offset = (left_offset + right_offset) / 2

            # Convert to gaze angles (relative to head pose)
            gaze_yaw = yaw_head + (avg_offset[0] * 30)  # Scale factor for sensitivity
            gaze_pitch = pitch_head + (avg_offset[1] * 30)

            return (gaze_pitch, gaze_yaw, roll_head)
        else:
            # Fallback: use head pose as gaze direction
            return head_pose

    def _calculate_eye_center(
        self,
        landmarks: np.ndarray,
        eye_indices: List[int]
    ) -> Tuple[float, float]:
        """Calculate center of eye from landmarks"""
        eye_landmarks = landmarks[eye_indices]
        center_x = np.mean(eye_landmarks[:, 0])
        center_y = np.mean(eye_landmarks[:, 1])
        return (center_x, center_y)

    def _project_gaze_to_plane(
        self,
        eye_left: Tuple[float, float],
        eye_right: Tuple[float, float],
        gaze_direction: Tuple[float, float, float]
    ) -> Tuple[float, float]:
        """
        Project gaze direction to 2D plane (frame)

        Args:
            eye_left: Left eye center (normalized)
            eye_right: Right eye center (normalized)
            gaze_direction: (pitch, yaw, roll) in degrees

        Returns:
            (x, y) estimated gaze target on frame
        """
        # Average eye position
        eye_x = (eye_left[0] + eye_right[0]) / 2
        eye_y = (eye_left[1] + eye_right[1]) / 2

        pitch, yaw, _ = gaze_direction

        # Convert angles to radians
        pitch_rad = pitch * np.pi / 180
        yaw_rad = yaw * np.pi / 180

        # Project gaze vector (simplified 2D projection)
        # Assume a distance of 1.0 units for projection
        projection_distance = 0.5

        target_x = eye_x + projection_distance * np.sin(yaw_rad)
        target_y = eye_y - projection_distance * np.sin(pitch_rad)

        # Clamp to frame bounds
        target_x = np.clip(target_x, 0.0, 1.0)
        target_y = np.clip(target_y, 0.0, 1.0)

        return (target_x, target_y)

    def _calculate_confidence(self, landmarks: np.ndarray) -> float:
        """
        Calculate confidence score based on landmark quality

        Args:
            landmarks: Face landmarks array

        Returns:
            Confidence score (0-1)
        """
        # Check if key landmarks are within reasonable bounds
        if len(landmarks) < 478:
            return 0.5

        # Check visibility (z-coordinate indicates depth)
        z_values = landmarks[:, 2]
        z_std = np.std(z_values)

        # Lower std = more planar face = better detection
        confidence = 1.0 - np.clip(z_std * 10, 0, 1)

        return confidence

    def _calculate_angle_difference(
        self,
        angle1: Tuple[float, float, float],
        angle2: Tuple[float, float, float]
    ) -> float:
        """Calculate Euclidean distance between two angle tuples"""
        diff = np.array(angle1) - np.array(angle2)
        return np.linalg.norm(diff)

    def update_fixation(
        self,
        tracking_id: str,
        person_id: Optional[int],
        gaze_data: GazeData,
        zones: List[Dict],
        timestamp: datetime
    ) -> Optional[GazeFixation]:
        """
        Update gaze fixation tracking

        Args:
            tracking_id: Person tracking ID
            person_id: Person ID (if known)
            gaze_data: GazeData object
            zones: List of zone dictionaries
            timestamp: Current timestamp

        Returns:
            GazeFixation object if fixation detected, None otherwise
        """
        # Determine target zone
        target_zone_id = None
        target_type = "unknown"

        if gaze_data.target_position:
            target_x, target_y = gaze_data.target_position

            # Check which zone the gaze target falls into
            for zone in zones:
                if not zone.get('is_active', True):
                    continue

                zone_polygon = zone.get('polygon', [])
                if self._point_in_polygon((target_x, target_y), zone_polygon):
                    target_zone_id = zone.get('id')
                    target_type = "zone"
                    break

        # Check if continuing existing fixation
        if tracking_id in self.active_fixations:
            fixation = self.active_fixations[tracking_id]

            # Check if gaze direction is stable
            angle_diff = self._calculate_angle_difference(
                gaze_data.gaze_direction,
                fixation.gaze_direction
            )

            if angle_diff < self.gaze_stability_threshold and target_zone_id == fixation.zone_id:
                # Update existing fixation
                fixation.last_update = timestamp
                fixation.gaze_direction = gaze_data.gaze_direction
                fixation.confidence = (fixation.confidence + gaze_data.confidence) / 2

                # Check if reached fixation threshold
                duration = (timestamp - fixation.fixation_start).total_seconds()
                if duration >= self.fixation_threshold:
                    return fixation
            else:
                # Gaze changed - end previous fixation and start new one
                self._end_fixation(tracking_id)

        # Create new fixation
        if target_zone_id is not None:
            fixation = GazeFixation(
                tracking_id=tracking_id,
                person_id=person_id,
                zone_id=target_zone_id,
                target_type=target_type,
                gaze_direction=gaze_data.gaze_direction,
                fixation_start=timestamp,
                last_update=timestamp,
                confidence=gaze_data.confidence
            )
            self.active_fixations[tracking_id] = fixation

        return None

    def _point_in_polygon(
        self,
        point: Tuple[float, float],
        polygon: List[List[float]]
    ) -> bool:
        """Check if point is inside polygon using ray casting"""
        x, y = point
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _end_fixation(self, tracking_id: str):
        """End active fixation for tracking ID"""
        if tracking_id in self.active_fixations:
            del self.active_fixations[tracking_id]

    def log_gaze_event_to_db(
        self,
        db: Session,
        tracking_id: str,
        person_id: Optional[int],
        gaze_data: GazeData,
        fixation: Optional[GazeFixation] = None,
        timestamp: datetime = None
    ):
        """
        Log gaze event to database

        Args:
            db: Database session
            tracking_id: Person tracking ID
            person_id: Person ID (if known)
            gaze_data: GazeData object
            fixation: GazeFixation object (if fixation detected)
            timestamp: Event timestamp
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)

        fixation_duration = 0.0
        is_fixation = False
        zone_id = None
        target_type = "unknown"

        if fixation:
            fixation_duration = (fixation.last_update - fixation.fixation_start).total_seconds()
            is_fixation = True
            zone_id = fixation.zone_id
            target_type = fixation.target_type

        # Create gaze event
        gaze_event = GazeEvent(
            person_id=person_id,
            body_tracking_id=tracking_id,
            timestamp=timestamp,
            zone_id=zone_id,
            target_type=target_type,
            target_position={
                'x': gaze_data.target_position[0] if gaze_data.target_position else None,
                'y': gaze_data.target_position[1] if gaze_data.target_position else None
            },
            gaze_direction={
                'pitch': gaze_data.gaze_direction[0],
                'yaw': gaze_data.gaze_direction[1],
                'roll': gaze_data.gaze_direction[2]
            },
            head_pose={
                'pitch': gaze_data.head_pose[0],
                'yaw': gaze_data.head_pose[1],
                'roll': gaze_data.head_pose[2]
            },
            fixation_duration_seconds=fixation_duration,
            confidence_score=gaze_data.confidence,
            is_fixation=is_fixation
        )

        db.add(gaze_event)
        db.commit()
        db.refresh(gaze_event)

        return gaze_event

    def cleanup_old_fixations(self, max_age_seconds: float = 5.0):
        """
        Remove fixations that haven't been updated recently

        Args:
            max_age_seconds: Maximum age before removal
        """
        current_time = datetime.now(UTC)
        keys_to_remove = []

        for tracking_id, fixation in self.active_fixations.items():
            age = (current_time - fixation.last_update).total_seconds()
            if age > max_age_seconds:
                keys_to_remove.append(tracking_id)

        for key in keys_to_remove:
            del self.active_fixations[key]

    def get_active_fixations(self) -> List[GazeFixation]:
        """Get all active gaze fixations"""
        return list(self.active_fixations.values())

    def release(self):
        """Release MediaPipe resources"""
        self.face_mesh.close()
