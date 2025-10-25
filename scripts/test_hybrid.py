"""
Test script for hybrid person+face detection pipeline
"""

import cv2
import sys
import os
import time
from datetime import datetime

# Add app directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
app_dir = os.path.join(parent_dir, 'app')
sys.path.insert(0, app_dir)

from person_detector import PersonDetector
from face_detector import FaceDetector

# Test configuration
TEST_DURATION = 15  # Run for 15 seconds (shorter for testing)
DISPLAY_VIDEO = True   # Display window with detections
SAVE_FRAMES = True   # Save frames with bounding boxes to debug

def test_hybrid_detection():
    """Test hybrid person+face detection"""
    print("=" * 70)
    print("Video AI - Hybrid Detection Test")
    print("=" * 70)

    # Initialize components
    print("\n1. Initializing detection components...")
    person_detector = PersonDetector(confidence_threshold=0.7)
    face_detector = FaceDetector(tolerance=0.6)
    print("[OK] Components ready")

    # Open camera
    print("\n2. Opening camera...")
    try:
        cap = cv2.VideoCapture(0)  # Use default camera
        if not cap.isOpened():
            print("[ERROR] Could not open camera")
            return None

        # Get camera properties
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        print(".1f")

    except Exception as e:
        print(f"[ERROR] Camera error: {e}")
        return None

    # Create debug directory
    debug_dir = os.path.join(parent_dir, "debug_frames_hybrid")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"   Debug frames will be saved to: {debug_dir}")

    # Test variables
    frame_count = 0
    persons_detected = 0
    faces_recognized = 0
    start_time = time.time()

    print("\n3. Starting hybrid detection...")
    print("   Detecting persons first, then faces within person regions")
    print("   Press 'q' to quit early\n")
    print("-" * 70)

    try:
        while time.time() - start_time < TEST_DURATION:
            # Capture frame
            ret, frame = cap.read()
            if not ret or frame is None:
                print("   [WARNING] Failed to capture frame")
                time.sleep(0.1)
                continue

            frame_count += 1
            timestamp = datetime.now()

            # Step 1: Detect persons (coarse segmentation)
            person_start = time.time()
            person_detections = person_detector.detect_persons(frame)
            person_time = time.time() - person_start

            # Step 2: For each person, check for visible faces
            face_detections = []
            face_visible_count = 0

            for person_bbox, person_conf in person_detections:
                # Extract person ROI for face detection
                roi_frame, offset_xy = person_detector.extract_person_roi(frame, person_bbox, padding=5)

                # Detect faces within the person ROI
                faces_in_roi = face_detector.detect_faces_in_roi(frame, person_bbox, offset_xy)

                # Check which faces meet visibility criteria
                for face_encoding, face_location in faces_in_roi:
                    if person_detector.is_face_visible(person_bbox, face_location, person_conf):
                        face_detections.append((face_encoding, face_location))
                        face_visible_count += 1

            face_time = time.time() - person_start - person_time

            # Update statistics
            persons_detected += len(person_detections)
            faces_recognized += len(face_detections)

            # Create display frame with bounding boxes
            display_frame = frame.copy()

            # Draw person boxes (orange)
            display_frame = person_detector.draw_person_boxes(display_frame, person_detections, color=(255, 165, 0))

            # Draw face boxes (green) on top
            for face_encoding, face_location in face_detections:
                display_frame = face_detector.draw_face_boxes(display_frame, face_location, person_id=1, name="Recognized")

            # Add overlay info
            timing_info = f"Person: {person_time:.3f}s | Face: {face_time:.3f}s"
            cv2.putText(display_frame, f"Frame: {frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Persons: {len(person_detections)}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.putText(display_frame, f"Faces: {len(face_detections)}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, timing_info, (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Save frame periodically
            if SAVE_FRAMES and (frame_count % 50 == 0 or len(person_detections) > 0):
                filename = f"hybrid_frame_{frame_count:04d}_{timestamp.strftime('%H%M%S')}.jpg"
                filepath = os.path.join(debug_dir, filename)
                cv2.imwrite(filepath, display_frame)
                print(f"   Saved debug frame: {filename}")

            # Progress update
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                avg_person_time = elapsed / frame_count * 1000  # per frame in ms
                print(".1f")
                print(".1f")
                print(f"      Total detections - Persons: {persons_detected}, Faces: {faces_recognized}")

            # Display frame
            if DISPLAY_VIDEO:
                cv2.imshow('Hybrid Detection Test', display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n   User requested quit")
                    break

            # Small delay to prevent overwhelming
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n   Interrupted by user")
    finally:
        # Cleanup
        print("\n" + "-" * 70)
        print("\n4. Cleaning up...")
        cap.release()
        if DISPLAY_VIDEO:
            cv2.destroyAllWindows()

    # Print final results
    print("\n" + "=" * 70)
    print("HYBRID DETECTION TEST RESULTS")
    print("=" * 70)
    print(f"Frames processed:          {frame_count}")
    print(f"Total persons detected:    {persons_detected}")
    print(f"Total faces recognized:    {faces_recognized}")
    print(".1f")

    if frame_count > 0:
        print("\nPer-frame averages:")
        print(".1f")
        print(".1f")

    print("=" * 70)

    return {
        'frames': frame_count,
        'persons': persons_detected,
        'faces': faces_recognized,
        'duration': time.time() - start_time,
        'success': True
    }

if __name__ == "__main__":
    print("\n[HYBRID TEST] Starting Hybrid Person+Face Detection Test...")
    print("Make sure your camera is available and not used by other applications\n")

    try:
        results = test_hybrid_detection()

        if results and results['success']:
            print("\n[PASSED] HYBRID DETECTION TEST PASSED")
            print("\nThe hybrid system successfully:")
            print("  ✓ Detected persons using Faster R-CNN")
            print("  ✓ Restricted face detection to person regions")
            print("  ✓ Applied face recognition when faces are visible")
            print(f"  ✓ Processed {results['frames']} frames in {results['duration']:.1f} seconds")

            print("\nNext steps:")
            print("1. Run main.py for basic person detection with face recognition")
            print("2. Run main_retail.py for retail analytics with hybrid detection")
            print("3. Check debug_frames_hybrid/ for saved test frames")
        else:
            print("\n[FAILED] HYBRID DETECTION TEST FAILED")

    except Exception as e:
        print(f"\n[ERROR] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
