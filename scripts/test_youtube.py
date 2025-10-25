"""
Simple test script for YouTube video input
Tests basic face detection and analytics with YouTube video
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

# Import core modules from app folder
from camera_manager import CameraManager
from face_detector import FaceDetector
from database import init_db, get_db

# YouTube video URL
YOUTUBE_URL = "https://www.youtube.com/watch?v=-1bRhYjw1qE"

# Test configuration
TEST_DURATION = 60  # Run for 60 seconds
DISPLAY_VIDEO = True  # Show video window


def test_youtube_detection():
    """Test face detection with YouTube video"""
    print("=" * 60)
    print("Video AI - YouTube Test")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    db = next(get_db())
    print("✓ Database initialized")

    # Initialize components
    print("\n2. Initializing components...")
    face_detector = FaceDetector(tolerance=0.6)
    face_detector.load_known_faces_from_db(db)
    print("✓ Face detector ready")

    # Initialize camera with YouTube URL
    print(f"\n3. Loading YouTube video...")
    print(f"   URL: {YOUTUBE_URL}")

    try:
        camera = CameraManager(source=YOUTUBE_URL, fps=10)
        camera.start()
        print("✓ YouTube video loaded")
    except Exception as e:
        print(f"✗ Error loading video: {e}")
        print("\nTrying alternative method (yt-dlp)...")
        print("If this fails, install: pip install yt-dlp")
        return

    # Wait for first frame
    print("\n4. Waiting for video to start...")
    time.sleep(3)

    # Test variables
    frame_count = 0
    faces_detected = 0
    persons_identified = {}
    start_time = time.time()

    print("\n5. Processing video...")
    print("   Press 'q' to quit early\n")
    print("-" * 60)

    try:
        while time.time() - start_time < TEST_DURATION:
            # Get current frame
            frame = camera.get_current_frame()

            if frame is None:
                time.sleep(0.1)
                continue

            frame_count += 1

            # Detect faces every 10 frames (to reduce processing)
            if frame_count % 10 == 0:
                detected_faces = face_detector.detect_faces(frame)

                if len(detected_faces) > 0:
                    faces_detected += len(detected_faces)

                    for face_encoding, face_location in detected_faces:
                        # Try to recognize
                        person_id = face_detector.recognize_face(face_encoding)

                        if not person_id:
                            # Add new person
                            person = face_detector.add_person_to_db(
                                db, face_encoding, frame, face_location
                            )
                            person_id = person.id
                            print(f"   [NEW] Person {person.name} detected (ID: {person_id})")
                        else:
                            # Update existing person
                            face_detector.update_person_visit(db, person_id)

                            if person_id not in persons_identified:
                                print(f"   [KNOWN] Person ID {person_id} recognized")

                        persons_identified[person_id] = persons_identified.get(person_id, 0) + 1

                        # Draw on frame
                        frame = face_detector.draw_face_boxes(
                            frame, face_location, person_id, f"Person {person_id}"
                        )

            # Display frame
            if DISPLAY_VIDEO:
                # Add info overlay
                cv2.putText(
                    frame,
                    f"Frame: {frame_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    frame,
                    f"Faces: {faces_detected}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    frame,
                    f"Persons: {len(persons_identified)}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                cv2.imshow('YouTube Video Test', frame)

                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n   User requested quit")
                    break

            # Progress update
            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                print(f"   Processed {frame_count} frames in {elapsed:.1f}s")

    except KeyboardInterrupt:
        print("\n   Interrupted by user")
    finally:
        # Cleanup
        print("\n" + "-" * 60)
        print("\n6. Cleaning up...")
        camera.stop()
        if DISPLAY_VIDEO:
            cv2.destroyAllWindows()

    # Print results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Frames processed:    {frame_count}")
    print(f"Total faces detected: {faces_detected}")
    print(f"Unique persons:      {len(persons_identified)}")
    print(f"Duration:            {time.time() - start_time:.1f}s")
    print("\nPerson Detection Details:")
    for person_id, count in persons_identified.items():
        print(f"  Person ID {person_id}: Detected {count} times")
    print("=" * 60)

    return {
        'frames': frame_count,
        'faces': faces_detected,
        'persons': len(persons_identified),
        'success': True
    }


if __name__ == "__main__":
    print("\n🎬 Starting YouTube Video Test...")
    print("This will test face detection on a YouTube video\n")

    try:
        results = test_youtube_detection()

        if results and results['success']:
            print("\n✅ TEST PASSED")
            print("\nNext steps:")
            print("1. Run full retail analytics: python main_retail.py")
            print("2. Access dashboard: http://localhost:8000")
        else:
            print("\n❌ TEST FAILED")

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
