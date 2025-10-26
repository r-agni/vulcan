"""
Hand & Pose Detection for Touch Interaction
Detects hand keypoints using MediaPipe Hands and classifies product interactions
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
    from app.core.database import ProductInteraction
except ImportError:
    from app.core.database import ProductInteraction


@dataclass
class HandDetection:
    """Data class for hand detection results"""
    hand_landmarks: List[Tuple[float, float, float]]  # (x, y, z) normalized coordinates
    handedness: str  # "Left" or "Right"
    confidence: float
    bbox: Tuple[float, float, float, float]  # (x_min, y_min, x_max, y_max)
    palm_center: Tuple[float, float]  # Center of palm


@dataclass
class Interaction:
    """Data class for product interaction"""
    person_id: Optional[int]
    tracking_id: str
    zone_id: int
    interaction_type: str  # reaching, touching, picking_up, examining, putting_back
    hand_position: Tuple[float, float]
    gesture_type: str  # pointing, grabbing, holding, open_palm
    confidence: float
    timestamp: datetime
    hand_landmarks: List[Tuple[float, float, float]]
    duration_seconds: float = 0.0


class InteractionDetector:
    """
    Detect hand gestures and classify product interactions using MediaPipe Hands
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        proximity_threshold: float = 0.15  # Normalized distance threshold
    ):
        """
        Initialize interaction detector

        Args:
            min_detection_confidence: Minimum confidence for hand detection
            min_tracking_confidence: Minimum confidence for hand tracking
            proximity_threshold: Maximum distance to consider interaction (normalized 0-1)
        """
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=4,  # Track up to 4 hands (2 people)
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.proximity_threshold = proximity_threshold

        # Active interactions: (tracking_id, zone_id) -> Interaction
        self.active_interactions: Dict[Tuple[str, int], Interaction] = {}

        # Gesture classification constants
        self.FINGER_TIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky
        self.FINGER_BASES = [2, 5, 9, 13, 17]

    def detect_hands(self, frame: np.ndarray) -> List[HandDetection]:
        """
        Detect hands in frame

        Args:
            frame: Input BGR frame

        Returns:
            List of HandDetection objects
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame
        results = self.hands.process(rgb_frame)

        hand_detections = []

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks,
                results.multi_handedness
            ):
                # Extract landmarks as list of (x, y, z) tuples
                landmarks = [
                    (lm.x, lm.y, lm.z)
                    for lm in hand_landmarks.landmark
                ]

                # Calculate bounding box
                x_coords = [lm[0] for lm in landmarks]
                y_coords = [lm[1] for lm in landmarks]
                bbox = (
                    min(x_coords),
                    min(y_coords),
                    max(x_coords),
                    max(y_coords)
                )

                # Calculate palm center (average of wrist and base of fingers)
                wrist = landmarks[0]
                palm_center = (
                    (wrist[0] + sum(landmarks[i][0] for i in self.FINGER_BASES) / 5) / 2,
                    (wrist[1] + sum(landmarks[i][1] for i in self.FINGER_BASES) / 5) / 2
                )

                hand_detection = HandDetection(
                    hand_landmarks=landmarks,
                    handedness=handedness.classification[0].label,
                    confidence=handedness.classification[0].score,
                    bbox=bbox,
                    palm_center=palm_center
                )

                hand_detections.append(hand_detection)

        return hand_detections

    def classify_gesture(self, hand: HandDetection) -> str:
        """
        Classify hand gesture type

        Args:
            hand: HandDetection object

        Returns:
            Gesture type string
        """
        landmarks = hand.hand_landmarks

        # Count extended fingers
        extended_fingers = 0

        # Check thumb (special case - check horizontal distance)
        thumb_tip = landmarks[4]
        thumb_base = landmarks[2]
        if hand.handedness == "Right":
            if thumb_tip[0] > thumb_base[0]:  # Thumb extended to right
                extended_fingers += 1
        else:  # Left hand
            if thumb_tip[0] < thumb_base[0]:  # Thumb extended to left
                extended_fingers += 1

        # Check other fingers (vertical distance)
        for i in range(1, 5):  # Index to Pinky
            tip = landmarks[self.FINGER_TIPS[i]]
            base = landmarks[self.FINGER_BASES[i]]
            if tip[1] < base[1]:  # Tip is higher than base (finger extended)
                extended_fingers += 1

        # Classify gesture based on extended fingers
        if extended_fingers == 0:
            return "grabbing"
        elif extended_fingers == 1:
            return "pointing"
        elif extended_fingers >= 4:
            return "open_palm"
        else:
            return "holding"

    def calculate_distance(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float]
    ) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def check_proximity_to_zone(
        self,
        hand_position: Tuple[float, float],
        zone_polygon: List[List[float]]
    ) -> Tuple[bool, float]:
        """
        Check if hand is near zone

        Args:
            hand_position: (x, y) normalized coordinates
            zone_polygon: List of [x, y] points defining zone

        Returns:
            (is_near, distance) tuple
        """
        # Calculate distance to zone centroid
        centroid_x = sum(p[0] for p in zone_polygon) / len(zone_polygon)
        centroid_y = sum(p[1] for p in zone_polygon) / len(zone_polygon)

        distance = self.calculate_distance(
            hand_position,
            (centroid_x, centroid_y)
        )

        is_near = distance < self.proximity_threshold

        return is_near, distance

    def classify_interaction_type(
        self,
        gesture: str,
        duration: float,
        previous_gesture: Optional[str] = None
    ) -> str:
        """
        Classify interaction type based on gesture and duration

        Args:
            gesture: Current gesture type
            duration: Interaction duration in seconds
            previous_gesture: Previous gesture (if any)

        Returns:
            Interaction type string
        """
        # Reaching: open palm or pointing, short duration
        if gesture in ["open_palm", "pointing"] and duration < 2.0:
            return "reaching"

        # Touching: any gesture, very short duration
        if duration < 1.0:
            return "touching"

        # Picking up: transition from open to grabbing
        if gesture == "grabbing" and previous_gesture == "open_palm":
            return "picking_up"

        # Examining: holding or pointing, medium duration
        if gesture in ["holding", "pointing"] and 2.0 <= duration < 10.0:
            return "examining"

        # Putting back: transition from grabbing to open
        if gesture == "open_palm" and previous_gesture == "grabbing" and duration > 1.0:
            return "putting_back"

        # Default: examining
        return "examining"

    def update(
        self,
        frame: np.ndarray,
        tracking_id: str,
        person_id: Optional[int],
        person_bbox: Tuple[int, int, int, int],
        zones: List[Dict],
        timestamp: datetime
    ) -> List[Interaction]:
        """
        Update interaction detection for a person

        Args:
            frame: Input frame
            tracking_id: Person tracking ID
            person_id: Person ID (if known)
            person_bbox: Person bounding box (left, top, right, bottom)
            zones: List of zone dictionaries
            timestamp: Current timestamp

        Returns:
            List of detected interactions
        """
        interactions = []

        # Crop frame to person bbox for hand detection
        left, top, right, bottom = person_bbox
        frame_height, frame_width = frame.shape[:2]

        # Add padding to bbox
        padding = 20
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(frame_width, right + padding)
        bottom = min(frame_height, bottom + padding)

        person_crop = frame[top:bottom, left:right]

        if person_crop.size == 0:
            return interactions

        # Detect hands in cropped region
        hands = self.detect_hands(person_crop)

        # Convert hand positions back to full frame coordinates
        crop_width = right - left
        crop_height = bottom - top

        for hand in hands:
            # Convert palm center to full frame normalized coordinates
            hand_x = (left + hand.palm_center[0] * crop_width) / frame_width
            hand_y = (top + hand.palm_center[1] * crop_height) / frame_height

            # Classify gesture
            gesture = self.classify_gesture(hand)

            # Check proximity to each zone
            for zone in zones:
                if not zone.get('is_active', True):
                    continue

                zone_id = zone.get('id')
                zone_polygon = zone.get('polygon', [])

                if not zone_id or not zone_polygon:
                    continue

                is_near, distance = self.check_proximity_to_zone(
                    (hand_x, hand_y),
                    zone_polygon
                )

                if is_near:
                    # Get or create interaction
                    key = (tracking_id, zone_id)

                    if key in self.active_interactions:
                        # Update existing interaction
                        active_int = self.active_interactions[key]
                        duration = (timestamp - active_int.timestamp).total_seconds()

                        # Classify interaction type
                        interaction_type = self.classify_interaction_type(
                            gesture,
                            duration,
                            active_int.gesture_type
                        )

                        # Update interaction
                        active_int.gesture_type = gesture
                        active_int.duration_seconds = duration
                        active_int.interaction_type = interaction_type
                        active_int.hand_position = (hand_x, hand_y)
                        active_int.hand_landmarks = hand.hand_landmarks

                        interactions.append(active_int)
                    else:
                        # Create new interaction
                        interaction = Interaction(
                            person_id=person_id,
                            tracking_id=tracking_id,
                            zone_id=zone_id,
                            interaction_type="reaching",
                            hand_position=(hand_x, hand_y),
                            gesture_type=gesture,
                            confidence=hand.confidence,
                            timestamp=timestamp,
                            hand_landmarks=hand.hand_landmarks,
                            duration_seconds=0.0
                        )

                        self.active_interactions[key] = interaction
                        interactions.append(interaction)

        return interactions

    def end_interaction(
        self,
        tracking_id: str,
        zone_id: int
    ) -> Optional[Interaction]:
        """
        End an active interaction and return it

        Args:
            tracking_id: Person tracking ID
            zone_id: Zone ID

        Returns:
            Completed Interaction object or None
        """
        key = (tracking_id, zone_id)
        if key in self.active_interactions:
            interaction = self.active_interactions.pop(key)
            return interaction
        return None

    def log_interaction_to_db(
        self,
        db: Session,
        interaction: Interaction
    ):
        """
        Log interaction to database

        Args:
            db: Database session
            interaction: Interaction object
        """
        # Calculate engagement score based on duration and interaction type
        engagement_score = 0.0

        if interaction.interaction_type == "touching":
            engagement_score = 0.3
        elif interaction.interaction_type == "reaching":
            engagement_score = 0.4
        elif interaction.interaction_type == "picking_up":
            engagement_score = 0.7
        elif interaction.interaction_type == "examining":
            engagement_score = 0.9
        elif interaction.interaction_type == "putting_back":
            engagement_score = 0.5

        # Boost score based on duration
        engagement_score = min(1.0, engagement_score + (interaction.duration_seconds / 30.0))

        # Create database record
        db_interaction = ProductInteraction(
            person_id=interaction.person_id,
            zone_id=interaction.zone_id,
            timestamp=interaction.timestamp,
            interaction_type=interaction.interaction_type,
            duration_seconds=interaction.duration_seconds,
            proximity_cm=None,  # Not calculated in this version
            engagement_score=engagement_score,
            # New columns for Phase 2
            hand_position={
                'x': interaction.hand_position[0],
                'y': interaction.hand_position[1]
            },
            gesture_type=interaction.gesture_type,
            interaction_confidence=interaction.confidence,
            hand_landmarks=[
                {'x': lm[0], 'y': lm[1], 'z': lm[2]}
                for lm in interaction.hand_landmarks
            ]
        )

        db.add(db_interaction)
        db.commit()
        db.refresh(db_interaction)

        return db_interaction

    def get_active_interactions(self) -> List[Interaction]:
        """Get all active interactions"""
        return list(self.active_interactions.values())

    def cleanup_old_interactions(self, max_age_seconds: float = 5.0):
        """
        Remove interactions that haven't been updated recently

        Args:
            max_age_seconds: Maximum age before removal
        """
        current_time = datetime.now(UTC)
        keys_to_remove = []

        for key, interaction in self.active_interactions.items():
            age = (current_time - interaction.timestamp).total_seconds()
            if age > max_age_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.active_interactions[key]

    def release(self):
        """Release MediaPipe resources"""
        self.hands.close()
