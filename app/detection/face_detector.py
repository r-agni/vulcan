import cv2
import numpy as np
from typing import List, Tuple, Optional
import pickle
from datetime import datetime
from sqlalchemy.orm import Session
try:
    from app.core.database import Person, DetectionEvent
    from app.utils.activity_logger import log_activity
except ImportError:
    from app.core.database import Person, DetectionEvent
    from app.utils.activity_logger import log_activity
import os
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
from scipy.spatial.distance import cosine


class FaceDetector:
    """Detect and recognize faces in video frames using facenet-pytorch and MTCNN"""

    def __init__(self, tolerance: float = 0.4):
        """
        Initialize face detector with facenet-pytorch backend

        Args:
            tolerance: Distance threshold for face matching (0.0-1.0, lower is stricter)
                      Default 0.4 works well for FaceNet embeddings with cosine distance
        """
        self.tolerance = tolerance
        self.known_face_encodings = []
        self.known_face_ids = []

        # Device configuration (GPU if available)
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        print(f'Face detector running on device: {self.device}')

        # Initialize MTCNN for face detection and alignment
        self.mtcnn = MTCNN(keep_all=True, device=self.device)

        # Initialize FaceNet model for embeddings (512-d vectors)
        self.model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)

        # Model name for compatibility
        self.model_name = "FaceNet-InceptionResnetV1-512d"

        # Initialize OpenCV face detector (Haar Cascade) as fallback
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

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
        log_activity(f"📋 Loaded {len(self.known_face_encodings)} known faces from database", "system")

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
        """
        Detect faces in a frame using facenet-pytorch and MTCNN
        Returns: List of (face_encoding, face_location, confidence) tuples
        """
        results = []

        try:
            # Convert BGR to RGB and create PIL Image for MTCNN
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(rgb_frame)

            # Detect faces using MTCNN
            boxes, probs = self.mtcnn.detect(pil_frame)

            if boxes is not None and len(boxes) > 0:
                # Get aligned faces (automatically preprocessed)
                faces = self.mtcnn(pil_frame)

                if faces is not None and len(faces) > 0:
                    # Generate embeddings for all faces at once
                    embeddings = self.model(faces).detach().cpu().numpy()

                    for i, box in enumerate(boxes):
                        x1, y1, x2, y2 = box  # MTCNN returns left, top, right, bottom

                        # Skip very small faces (likely false positives)
                        width, height = x2 - x1, y2 - y1
                        if width < 50 or height < 50:
                            continue

                        # Convert to (top, right, bottom, left) format to match original API
                        face_location = (int(y1), int(x2), int(y2), int(x1))

                        # Get corresponding embedding and confidence
                        face_encoding = embeddings[i]
                        face_confidence = float(probs[i])

                        results.append((face_encoding, face_location, face_confidence))

        except Exception as e:
            print(f"Error detecting faces with facenet-pytorch: {e}")
            # Fallback to OpenCV Haar Cascade if facenet-pytorch fails
            results = self._detect_faces_opencv(frame)

        return results

    def detect_faces_in_roi(self, frame: np.ndarray, roi_bbox: Tuple[int, int, int, int],
                           offset_xy: Tuple[int, int] = (0, 0)) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
        """
        Detect faces in a specific region of interest (ROI) using facenet-pytorch and MTCNN
        Useful for hybrid detection where we only want faces within detected person regions

        Args:
            frame: Full frame image
            roi_bbox: Region of interest bbox (left, top, right, bottom)
            offset_xy: Offset to add to face locations to convert back to full frame coordinates

        Returns: List of (face_encoding, face_location, confidence) tuples with global coordinates
        """
        results = []

        try:
            # Extract ROI from frame
            roi_left, roi_top, roi_right, roi_bottom = roi_bbox
            roi_frame = frame[roi_top:roi_bottom, roi_left:roi_right]

            if roi_frame.size == 0:
                return results

            # Convert BGR to RGB and create PIL Image for MTCNN
            rgb_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2RGB)
            pil_roi = Image.fromarray(rgb_roi)

            # Detect faces in ROI using MTCNN
            boxes, probs = self.mtcnn.detect(pil_roi)

            if boxes is not None and len(boxes) > 0:
                # Get aligned faces (automatically preprocessed)
                faces = self.mtcnn(pil_roi)

                if faces is not None and len(faces) > 0:
                    # Generate embeddings for all faces at once
                    embeddings = self.model(faces).detach().cpu().numpy()

                    for i, box in enumerate(boxes):
                        x1, y1, x2, y2 = box  # MTCNN returns left, top, right, bottom (relative to ROI)

                        # Skip very small faces (likely false positives)
                        width, height = x2 - x1, y2 - y1
                        if width < 30 or height < 30:  # Smaller threshold for ROI detection
                            continue

                        # Convert ROI coordinates back to full frame coordinates
                        global_x1 = x1 + roi_left + offset_xy[0]
                        global_y1 = y1 + roi_top + offset_xy[1]
                        global_x2 = x2 + roi_left + offset_xy[0]
                        global_y2 = y2 + roi_top + offset_xy[1]

                        # Convert to (top, right, bottom, left) format to match original API
                        face_location = (int(global_y1), int(global_x2), int(global_y2), int(global_x1))

                        # Get corresponding embedding and confidence
                        face_encoding = embeddings[i]
                        face_confidence = float(probs[i])

                        results.append((face_encoding, face_location, face_confidence))

        except Exception as e:
            print(f"Error detecting faces in ROI: {e}")
            # Fallback to OpenCV Haar Cascade in ROI
            results = self._detect_faces_opencv_in_roi(frame, roi_bbox, offset_xy)

        return results

    def _detect_faces_opencv_in_roi(self, frame: np.ndarray, roi_bbox: Tuple[int, int, int, int],
                                   offset_xy: Tuple[int, int] = (0, 0)) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
        """
        Fallback face detection in ROI using OpenCV Haar Cascade
        """
        results = []

        try:
            # Extract ROI
            roi_left, roi_top, roi_right, roi_bottom = roi_bbox
            roi_frame = frame[roi_top:roi_bottom, roi_left:roi_right]

            if roi_frame.size == 0:
                return results

            # Convert to grayscale and detect faces
            gray_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
            faces_roi = self.face_cascade.detectMultiScale(gray_roi, 1.1, 4)  # More sensitive for ROI

            for (x, y, w, h) in faces_roi:
                try:
                    # Extract face region and convert to PIL for facenet-pytorch
                    face_img = roi_frame[y:y+h, x:x+w]
                    pil_face = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))

                    # Get aligned face using MTCNN (single face)
                    mtcnn_single = MTCNN(keep_all=False, device=self.device)
                    aligned_face = mtcnn_single(pil_face)

                    if aligned_face is not None:
                        # Generate embedding
                        embedding = self.model(aligned_face.unsqueeze(0)).detach().cpu().numpy().flatten()

                        # Convert coordinates back to full frame
                        global_x = x + roi_left + offset_xy[0]
                        global_y = y + roi_top + offset_xy[1]

                        # Convert to (top, right, bottom, left) format
                        face_location = (global_y, global_x + w, global_y + h, global_x)

                        results.append((embedding, face_location, 0.8))

                except Exception as e:
                    print(f"Error generating face embedding in ROI: {e}")
                    continue

        except Exception as e:
            print(f"Error in OpenCV ROI face detection: {e}")

        return results

    def _detect_faces_opencv(self, frame: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
        """
        Fallback face detection using OpenCV Haar Cascade + facenet-pytorch embeddings
        """
        results = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            # Convert to (top, right, bottom, left) format
            face_location = (y, x + w, y + h, x)

            try:
                # Extract face region and convert to PIL for facenet-pytorch
                face_img = frame[y:y+h, x:x+w]
                pil_face = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))

                # Get aligned face using MTCNN (single face)
                mtcnn_single = MTCNN(keep_all=False, device=self.device)
                aligned_face = mtcnn_single(pil_face)

                if aligned_face is not None:
                    # Generate embedding
                    embedding = self.model(aligned_face.unsqueeze(0)).detach().cpu().numpy().flatten()
                    results.append((embedding, face_location, 0.8))

            except Exception as e:
                print(f"Error generating face embedding with OpenCV fallback: {e}")
                continue

        return results

    def recognize_face(self, face_encoding: np.ndarray, debug: bool = False) -> Optional[int]:
        """
        Match a face encoding against known faces using cosine distance
        Returns: person_id if match found, None otherwise
        """
        if len(self.known_face_encodings) == 0:
            return None

        log_activity(f"🔎 Matching face against {len(self.known_face_encodings)} known faces...", "detection")

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

            if debug:
                print(f"      Best match distance: {best_distance:.4f} (tolerance: {self.tolerance:.4f})")

            # Check if the best match is within tolerance
            if best_distance <= self.tolerance:
                person_id = self.known_face_ids[best_match_index]
                log_activity(f"✓ Face match found (confidence: {(1-best_distance)*100:.1f}%)", "detection")
                return person_id

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
        os.makedirs("data/uploads/thumbnails", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        thumbnail_path = f"data/uploads/thumbnails/person_{timestamp}.jpg"
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

        # Also add to merged_logs users table
        try:
            from merged_logs import MergedLogger
            merged_logger = MergedLogger()
            merged_logger.create_or_update_user(
                person_id=person.id,
                name=person.name,
                face_encoding=pickle.dumps(face_encoding),
                thumbnail_path=thumbnail_path
            )
            print(f"Added person to merged logs: {person.name} (ID: {person.id})")
        except Exception as e:
            print(f"Error adding to merged logs: {e}")

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

        # Make sure coordinates are within frame bounds to prevent errors
        height, width = frame.shape[:2]
        left = max(0, min(left, width-1))
        right = max(0, min(right, width-1))
        top = max(0, min(top, height-1))
        bottom = max(0, min(bottom, height-1))

        # Draw box (increased thickness for better visibility)
        color = (0, 255, 0) if person_id else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 4)  # Increased from 2 to 4

        # Draw label background with better positioning
        label = name if name else f"ID: {person_id}" if person_id else "Unknown"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.8, 2)[0]
        label_width, label_height = label_size

        # Ensure label background doesn't go outside frame
        label_bg_top = max(0, top - 40)
        label_bg_left = left
        label_bg_right = min(width-1, left + label_width + 12)
        label_bg_bottom = min(height-1, top - 5)

        cv2.rectangle(frame, (label_bg_left, label_bg_top), (label_bg_right, label_bg_bottom), color, cv2.FILLED)

        # Draw label text with better contrast
        cv2.putText(
            frame,
            label,
            (left + 6, max(label_bg_bottom - 10, 20)),
            cv2.FONT_HERSHEY_DUPLEX,
            0.8,  # Slightly larger
            (255, 255, 255),
            2     # Thicker text
        )

        return frame
