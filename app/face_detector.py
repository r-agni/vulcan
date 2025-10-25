import face_recognition
import cv2
import numpy as np
from typing import List, Tuple, Optional
import pickle
from datetime import datetime
from sqlalchemy.orm import Session
from database import Person, DetectionEvent
import os


class FaceDetector:
    """Detect and recognize faces in video frames"""

    def __init__(self, tolerance: float = 0.6):
        self.tolerance = tolerance
        self.known_face_encodings = []
        self.known_face_ids = []

    def load_known_faces_from_db(self, db: Session):
        """Load all known face encodings from database"""
        persons = db.query(Person).all()
        self.known_face_encodings = []
        self.known_face_ids = []

        for person in persons:
            if person.face_encoding:
                encoding = pickle.loads(person.face_encoding)
                self.known_face_encodings.append(encoding)
                self.known_face_ids.append(person.id)

        print(f"Loaded {len(self.known_face_encodings)} known faces from database")

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Detect faces in a frame
        Returns: List of (face_encoding, face_location) tuples
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Find face locations and encodings
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        return list(zip(face_encodings, face_locations))

    def recognize_face(self, face_encoding: np.ndarray) -> Optional[int]:
        """
        Match a face encoding against known faces
        Returns: person_id if match found, None otherwise
        """
        if len(self.known_face_encodings) == 0:
            return None

        # Compare face encoding with known faces
        matches = face_recognition.compare_faces(
            self.known_face_encodings,
            face_encoding,
            tolerance=self.tolerance
        )

        # Find best match
        face_distances = face_recognition.face_distance(
            self.known_face_encodings,
            face_encoding
        )

        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                return self.known_face_ids[best_match_index]

        return None

    def add_person_to_db(
        self,
        db: Session,
        face_encoding: np.ndarray,
        frame: np.ndarray,
        face_location: Tuple[int, int, int, int],
        name: Optional[str] = None
    ) -> Person:
        """
        Add a new person to the database
        """
        # Extract face thumbnail
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]

        # Save thumbnail
        os.makedirs("uploads/thumbnails", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        thumbnail_path = f"uploads/thumbnails/person_{timestamp}.jpg"
        cv2.imwrite(thumbnail_path, face_image)

        # Create person record
        person = Person(
            name=name or f"Person_{timestamp}",
            face_encoding=pickle.dumps(face_encoding),
            thumbnail_path=thumbnail_path,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            visit_count=1
        )

        db.add(person)
        db.commit()
        db.refresh(person)

        # Update local cache
        self.known_face_encodings.append(face_encoding)
        self.known_face_ids.append(person.id)

        print(f"Added new person to database: {person.name} (ID: {person.id})")
        return person

    def update_person_visit(self, db: Session, person_id: int):
        """Update person's last seen time and visit count"""
        person = db.query(Person).filter(Person.id == person_id).first()
        if person:
            person.last_seen = datetime.utcnow()
            person.visit_count += 1
            db.commit()

    def log_detection_event(
        self,
        db: Session,
        person_id: Optional[int],
        confidence: float,
        frame_path: Optional[str] = None
    ) -> DetectionEvent:
        """Log a detection event"""
        event = DetectionEvent(
            person_id=person_id,
            confidence=confidence,
            frame_path=frame_path,
            timestamp=datetime.utcnow()
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def draw_face_boxes(
        self,
        frame: np.ndarray,
        face_location: Tuple[int, int, int, int],
        person_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> np.ndarray:
        """Draw bounding box around detected face"""
        top, right, bottom, left = face_location

        # Draw box
        color = (0, 255, 0) if person_id else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        # Draw label
        label = name if name else f"ID: {person_id}" if person_id else "Unknown"
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(
            frame,
            label,
            (left + 6, bottom - 6),
            cv2.FONT_HERSHEY_DUPLEX,
            0.6,
            (255, 255, 255),
            1
        )

        return frame
