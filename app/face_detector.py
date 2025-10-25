import cv2
import numpy as np
from typing import List, Tuple, Optional
import pickle
from datetime import datetime
from sqlalchemy.orm import Session
from database import Person, DetectionEvent
import os
from deepface import DeepFace
from scipy.spatial.distance import cosine


class FaceDetector:
    """Detect and recognize faces in video frames using DeepFace and OpenCV"""

    def __init__(self, tolerance: float = 0.4):
        """
        Initialize face detector with DeepFace backend

        Args:
            tolerance: Distance threshold for face matching (0.0-1.0, lower is stricter)
                      Default 0.4 works well for DeepFace with cosine distance
        """
        self.tolerance = tolerance
        self.known_face_encodings = []
        self.known_face_ids = []

        # Initialize OpenCV face detector (Haar Cascade) as fallback
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        # DeepFace model backend (options: VGG-Face, Facenet, OpenFace, DeepFace, DeepID, ArcFace, Dlib)
        self.model_name = "Facenet"  # Facenet works well on Windows without dlib
        self.detector_backend = "opencv"  # Use opencv instead of dlib

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
        Detect faces in a frame using DeepFace
        Returns: List of (face_encoding, face_location) tuples
        """
        results = []

        try:
            # Use DeepFace to detect and extract faces
            # Convert BGR to RGB for DeepFace
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces using DeepFace
            face_objs = DeepFace.extract_faces(
                img_path=rgb_frame,
                detector_backend=self.detector_backend,
                enforce_detection=False,
                align=True
            )

            for face_obj in face_objs:
                # Get face location
                facial_area = face_obj['facial_area']
                x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']

                # Convert to (top, right, bottom, left) format to match original API
                face_location = (y, x + w, y + h, x)

                # Extract face region for embedding
                face_img = face_obj['face']

                # Get face embedding using DeepFace
                try:
                    embedding_objs = DeepFace.represent(
                        img_path=face_img,
                        model_name=self.model_name,
                        detector_backend=self.detector_backend,
                        enforce_detection=False
                    )

                    if embedding_objs and len(embedding_objs) > 0:
                        face_encoding = np.array(embedding_objs[0]['embedding'])
                        results.append((face_encoding, face_location))

                except Exception as e:
                    print(f"Error generating face embedding: {e}")
                    continue

        except Exception as e:
            print(f"Error detecting faces: {e}")
            # Fallback to OpenCV Haar Cascade if DeepFace fails
            results = self._detect_faces_opencv(frame)

        return results

    def _detect_faces_opencv(self, frame: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Fallback face detection using OpenCV Haar Cascade
        """
        results = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            # Extract face region
            face_img = frame[y:y+h, x:x+w]

            # Convert to (top, right, bottom, left) format
            face_location = (y, x + w, y + h, x)

            try:
                # Get embedding using DeepFace
                embedding_objs = DeepFace.represent(
                    img_path=cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB),
                    model_name=self.model_name,
                    detector_backend=self.detector_backend,
                    enforce_detection=False
                )

                if embedding_objs and len(embedding_objs) > 0:
                    face_encoding = np.array(embedding_objs[0]['embedding'])
                    results.append((face_encoding, face_location))

            except Exception as e:
                print(f"Error generating face embedding with OpenCV fallback: {e}")
                continue

        return results

    def recognize_face(self, face_encoding: np.ndarray) -> Optional[int]:
        """
        Match a face encoding against known faces using cosine distance
        Returns: person_id if match found, None otherwise
        """
        if len(self.known_face_encodings) == 0:
            return None

        # Calculate cosine distances between the face encoding and all known faces
        distances = []
        for known_encoding in self.known_face_encodings:
            # Compute cosine distance (1 - cosine similarity)
            distance = cosine(face_encoding, known_encoding)
            distances.append(distance)

        distances = np.array(distances)

        # Find the best match (minimum distance)
        if len(distances) > 0:
            best_match_index = np.argmin(distances)
            best_distance = distances[best_match_index]

            # Check if the best match is within tolerance
            if best_distance <= self.tolerance:
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
