"""
Simple test script for YouTube video input
Tests basic face detection and analytics with YouTube video
"""

import cv2
import sys
import os
import time
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
YOUTUBE_URL = "https://www.youtube.com/watch?v=KMJS66jBtVQ"

# Test configuration
TEST_DURATION = 30  # Run for 30 seconds (shorter for testing)
DISPLAY_VIDEO = True   # Try displaying window (may work now)
SAVE_FRAMES = True   # Save frames with bounding boxes to debug visibility


def test_youtube_detection():
    """Test face detection with YouTube video"""
    print("=" * 60)
    print("Video AI - YouTube Test")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database...")

    # Clear existing database for fresh test (important when switching face recognition models)
    # The database is in data/database/video_ai.db by default
    db_paths_to_check = [
        os.path.join(parent_dir, 'data', 'database', 'video_ai.db'),
        os.path.join(parent_dir, 'data', 'database', 'surveillance.db'),
        os.path.join(parent_dir, 'video_ai.db'),
        os.path.join(parent_dir, 'surveillance.db'),
        os.path.join(parent_dir, 'app', 'video_ai.db'),
        os.path.join(parent_dir, 'app', 'surveillance.db')
    ]

    for db_path in db_paths_to_check:
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"   Cleared existing database: {db_path}")

    init_db()
    db = next(get_db())
    print("[OK] Database initialized")

    # Initialize components
    print("\n2. Initializing components...")
    # Use moderate tolerance (0.4) for better person distinction
    # For Facenet with cosine distance: 0.3-0.5 works well for distinguishing people
    face_detector = FaceDetector(tolerance=0.4)
    face_detector.load_known_faces_from_db(db)
    print(f"[OK] Face detector ready ({face_detector.model_name} model, tolerance: {face_detector.tolerance:.2f})")

    # Initialize camera with YouTube URL
    print(f"\n3. Loading YouTube video...")
    print(f"   URL: {YOUTUBE_URL}")

    try:
        camera = CameraManager(camera_source=YOUTUBE_URL, fps=10)
        camera.start()
        print("[OK] YouTube video loaded")
    except Exception as e:
        print(f"[ERROR] Error loading video: {e}")
        print("\nTrying alternative method (yt-dlp)...")
        print("If this fails, install: pip install yt-dlp")
        return

    # Get first frame to check video properties
    initial_frame = camera.get_current_frame()
    if initial_frame is not None:
        h, w = initial_frame.shape[:2]
        print(f"   Video dimensions: {w}x{h}")
    else:
        print("   Warning: Could not get initial frame")

    # Wait for first frame
    print("\n4. Waiting for video to start...")
    time.sleep(3)

    # Create debug directory for saved frames
    debug_dir = os.path.join(parent_dir, "debug_frames")
    os.makedirs(debug_dir, exist_ok=True)
    print(f"   Debug frames will be saved to: {debug_dir}")

    # Test variables
    frame_count = 0
    faces_detected = 0
    persons_identified = {}
    start_time = time.time()
    current_faces = []  # Store current frame's detected faces

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

            # Detect faces every frame for better accuracy
            current_faces = []  # Clear previous faces
            detected_faces = face_detector.detect_faces(frame)

            if len(detected_faces) > 0:
                faces_detected += len(detected_faces)

                for face_encoding, face_location in detected_faces:
                    # Try to recognize (with debug output)
                    person_id = face_detector.recognize_face(face_encoding, debug=True)

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

                    # Store face info for drawing
                    current_faces.append((face_location, person_id))

            # Create display frame with bounding boxes
            display_frame = frame.copy() if frame is not None else None

            if display_frame is not None:
                # Draw all current faces on the display frame
                for face_location, person_id in current_faces:
                    print(f"   Drawing box: location={face_location}, person_id={person_id}")
                    display_frame = face_detector.draw_face_boxes(
                        display_frame, face_location, person_id, f"ID: {person_id}"
                    )

                # Add count of faces in current frame
                if len(current_faces) > 0:
                    cv2.putText(
                        display_frame,
                        f"Faces in frame: {len(current_faces)}",
                        (10, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 165, 255),
                        2
                    )
                    print(f"   Frame {frame_count}: Drawing {len(current_faces)} bounding boxes")

                    # Save frame with bounding boxes
                    if SAVE_FRAMES:
                        timestamp = datetime.now().strftime("%H%M%S_%f")
                        filename = f"frame_{frame_count:04d}_{timestamp}.jpg"
                        filepath = os.path.join(debug_dir, filename)
                        cv2.imwrite(filepath, display_frame)
                        print(f"   Saved debug frame: {filename}")

                elif frame_count % 30 == 0:  # Print every 30 frames when no faces
                    print(f"   Frame {frame_count}: No faces detected")
                    # Save sample frame to check video quality
                    if SAVE_FRAMES and frame_count % 100 == 0:
                        timestamp = datetime.now().strftime("%H%M%S_%f")
                        filename = f"no_faces_frame_{frame_count:04d}_{timestamp}.jpg"
                        filepath = os.path.join(debug_dir, filename)
                        cv2.imwrite(filepath, display_frame)
                        print(f"   Saved sample frame: {filename}")

            # Display frame
            if DISPLAY_VIDEO:
                # Add info overlay on display_frame
                cv2.putText(
                    display_frame,
                    f"Frame: {frame_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    display_frame,
                    f"Faces: {faces_detected}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    display_frame,
                    f"Persons: {len(persons_identified)}",
                    (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                cv2.imshow('YouTube Video Test', display_frame)

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
    print("\n[VIDEO TEST] Starting YouTube Video Test...")
    print("This will test face detection on a YouTube video\n")

    try:
        results = test_youtube_detection()

        if results and results['success']:
            print("\n[PASSED] TEST PASSED")
            print("\nNext steps:")
            print("1. Run full retail analytics: python main_retail.py")
            print("2. Access dashboard: http://localhost:8000")
        else:
            print("\n[FAILED] TEST FAILED")

    except Exception as e:
        print(f"\n[ERROR] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
