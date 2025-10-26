"""Detection modules for person, face, body, gaze, and interaction detection."""
from .person_detector import PersonDetector
from .face_detector import FaceDetector
from .body_tracker import BodyTracker
from .gaze_detector import GazeDetector
from .interaction_detector import InteractionDetector

__all__ = [
    'PersonDetector',
    'FaceDetector',
    'BodyTracker',
    'GazeDetector',
    'InteractionDetector'
]
