"""
Person Detector using Faster R-CNN with ResNet-50 backbone
Provides coarse person segmentation for hybrid detection pipeline
"""

import cv2
import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FasterRCNN_ResNet50_FPN_Weights
import numpy as np
from typing import List, Tuple, Optional
import time


class PersonDetector:
    """Detect persons in video frames using Faster R-CNN"""

    def __init__(self, confidence_threshold: float = 0.7, device: Optional[str] = None):
        """
        Initialize person detector with Faster R-CNN

        Args:
            confidence_threshold: Minimum confidence for person detection (0.0-1.0)
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        self.confidence_threshold = confidence_threshold

        # Device configuration
        if device is None:
            self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        print(f'Person detector running on device: {self.device}')

        # Load pre-trained Faster R-CNN model
        self.model = fasterrcnn_resnet50_fpn(
            weights=FasterRCNN_ResNet50_FPN_Weights.COCO_V1,
            progress=True
        )

        # Set to evaluation mode
        self.model.eval()
        self.model.to(self.device)

        # COCO class labels (person = 1)
        self.person_class_id = 1

        # Warm up the model
        self._warm_up()

        print(f'Person detector initialized (threshold: {self.confidence_threshold})')

    def _warm_up(self):
        """Warm up the model with a dummy input"""
        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
        with torch.no_grad():
            self.model(dummy_input)

    def detect_persons(self, frame: np.ndarray) -> List[Tuple[Tuple[int, int, int, int], float]]:
        """
        Detect persons in a frame

        Args:
            frame: BGR image frame

        Returns:
            List of (bbox, confidence) tuples where bbox is (left, top, right, bottom)
        """
        if frame is None or frame.size == 0:
            return []

        try:
            # Convert BGR to RGB and normalize to [0, 1]
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

            # Convert to tensor and add batch dimension (C, H, W)
            tensor_frame = torch.from_numpy(rgb_frame).permute(2, 0, 1).unsqueeze(0)

            # Move to device
            tensor_frame = tensor_frame.to(self.device)

            # Run inference
            with torch.no_grad():
                predictions = self.model(tensor_frame)

            # Extract results (predictions is a list with one element for single image)
            pred = predictions[0]

            # Get boxes, labels, and scores
            boxes = pred['boxes'].cpu().numpy()
            labels = pred['labels'].cpu().numpy()
            scores = pred['scores'].cpu().numpy()

            # Filter for persons above confidence threshold
            person_indices = (labels == self.person_class_id) & (scores >= self.confidence_threshold)

            results = []
            for i, is_person in enumerate(person_indices):
                if is_person:
                    box = boxes[i].astype(int)
                    # Convert from (x1, y1, x2, y2) to (left, top, right, bottom)
                    left, top, right, bottom = box
                    bbox = (left, top, right, bottom)
                    confidence = float(scores[i])

                    # Filter out very small detections (likely noise)
                    width, height = right - left, bottom - top
                    if width >= 50 and height >= 100:  # Minimum reasonable person size
                        results.append((bbox, confidence))

            return results

        except Exception as e:
            print(f"Error in person detection: {e}")
            return []

    def is_face_visible(self, person_bbox: Tuple[int, int, int, int],
                       face_bbox: Tuple[int, int, int, int],
                       face_confidence: float = 0.8) -> bool:
        """
        Determine if a detected face is sufficiently visible for recognition

        Args:
            person_bbox: Person bounding box (left, top, right, bottom)
            face_bbox: Face bounding box (top, right, bottom, left) - Note: different format!
            face_confidence: Minimum face detection confidence

        Returns:
            True if face is visible and meets criteria
        """
        try:
            # Convert face bbox to same format as person bbox (left, top, right, bottom)
            face_top, face_right, face_bottom, face_left = face_bbox
            face_bbox_normalized = (face_left, face_top, face_right, face_bottom)

            person_left, person_top, person_right, person_bottom = person_bbox
            face_left, face_top, face_right, face_bottom = face_bbox_normalized

            # Check if face bbox intersects with person bbox
            # Calculate intersection area
            inter_left = max(person_left, face_left)
            inter_top = max(person_top, face_top)
            inter_right = min(person_right, face_right)
            inter_bottom = min(person_bottom, face_bottom)

            if inter_right <= inter_left or inter_bottom <= inter_top:
                # No intersection
                return False

            inter_area = (inter_right - inter_left) * (inter_bottom - inter_top)
            face_area = (face_right - face_left) * (face_bottom - face_top)
            person_area = (person_right - person_left) * (person_bottom - person_top)

            # Face must overlap significantly with person
            overlap_ratio = inter_area / face_area if face_area > 0 else 0
            if overlap_ratio < 0.5:  # At least 50% of face must be within person bbox
                return False

            # Face must be reasonably sized relative to person
            face_height = face_bottom - face_top
            person_height = person_bottom - person_top
            size_ratio = face_height / person_height if person_height > 0 else 0

            # Face should be at least 15% of person height (adjustable threshold)
            if size_ratio < 0.15:
                return False

            # Face confidence must be above threshold
            if face_confidence < 0.8:
                return False

            return True

        except Exception as e:
            print(f"Error checking face visibility: {e}")
            return False

    def extract_person_roi(self, frame: np.ndarray, person_bbox: Tuple[int, int, int, int],
                          padding: int = 20) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        Extract person region of interest with padding

        Args:
            frame: Original frame
            person_bbox: Person bounding box (left, top, right, bottom)
            padding: Pixels to pad around bbox

        Returns:
            (cropped_image, offset_xy) where offset_xy is (x_offset, y_offset)
        """
        try:
            h, w = frame.shape[:2]
            left, top, right, bottom = person_bbox

            # Apply padding
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(w - 1, right + padding)
            bottom = min(h - 1, bottom + padding)

            # Extract ROI
            roi = frame[top:bottom, left:right].copy()
            offset_xy = (left, top)

            return roi, offset_xy

        except Exception as e:
            print(f"Error extracting person ROI: {e}")
            return frame, (0, 0)

    def draw_person_boxes(self, frame: np.ndarray,
                         detections: List[Tuple[Tuple[int, int, int, int], float]],
                         color: Tuple[int, int, int] = (255, 165, 0)) -> np.ndarray:
        """
        Draw bounding boxes around detected persons

        Args:
            frame: Frame to draw on
            detections: List of (bbox, confidence) tuples
            color: BGR color tuple (orange by default)

        Returns:
            Frame with bounding boxes drawn
        """
        for bbox, confidence in detections:
            left, top, right, bottom = bbox

            # Ensure coordinates are within bounds
            h, w = frame.shape[:2]
            left = max(0, min(left, w-1))
            right = max(0, min(right, w-1))
            top = max(0, min(top, h-1))
            bottom = max(0, min(bottom, h-1))

            # Draw rectangle
            cv2.rectangle(frame, (left, top), (right, bottom), color, 3)

            # Draw label
            label = f"Person: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 2)[0]
            label_width, label_height = label_size

            # Background rectangle for label
            cv2.rectangle(frame, (left, top - 25), (left + label_width + 10, top), color, cv2.FILLED)

            # Label text
            cv2.putText(frame, label, (left + 5, top - 5),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        return frame

    def get_processing_time(self) -> float:
        """Get average processing time (can be extended for performance monitoring)"""
        # Placeholder for future performance monitoring
        return 0.0


# Example usage for testing
if __name__ == "__main__":
    import time

    # Initialize detector
    detector = PersonDetector(confidence_threshold=0.7)

    # Test with a dummy frame
    dummy_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    start_time = time.time()
    detections = detector.detect_persons(dummy_frame)
    end_time = time.time()

    print(f"Detected {len(detections)} persons in {end_time - start_time:.3f}s")
    for i, (bbox, conf) in enumerate(detections):
        print(f"  Person {i+1}: bbox={bbox}, confidence={conf:.3f}")
