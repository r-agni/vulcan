"""
Main Application - Retail Analytics Edition
Integrated video surveillance with advanced retail analytics
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json
import cv2
import os
from typing import List, Dict
from datetime import datetime, timedelta
import threading
import time

from database import (
    init_db, get_db, Person, DetectionEvent, BehaviorAnalysis,
    Zone, VirtualLine, OccupancyLog
)
from camera_manager import CameraManager
from face_detector import FaceDetector
from person_detector import PersonDetector
from gemini_analyzer import GeminiAnalyzer
from retail_analytics import (
    TrajectoryTracker, DwellTimeCalculator, ZoneDetector,
    OccupancyCounter, LineCrossingDetector, HeatmapGenerator, QueueDetector
)
from video_overlay import VideoOverlayRenderer
from zone_manager import router as zone_router, create_default_zones, create_default_lines
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Retail Video Analytics System")

# Include zone management router
app.include_router(zone_router)

# Initialize core components
camera = CameraManager(camera_source=int(os.getenv("CAMERA_SOURCE", 0)))
face_detector = FaceDetector(tolerance=0.6)
person_detector = PersonDetector(confidence_threshold=0.7)
gemini_analyzer = GeminiAnalyzer(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize retail analytics modules
trajectory_tracker = TrajectoryTracker(history_duration_seconds=30)
dwell_calculator = DwellTimeCalculator()
zone_detector = ZoneDetector()
occupancy_counter = OccupancyCounter()
line_crossing_detector = LineCrossingDetector()
heatmap_generator = HeatmapGenerator()
queue_detector = QueueDetector()
overlay_renderer = VideoOverlayRenderer()

# WebSocket connections
active_connections: List[WebSocket] = []

# Global state
current_detected_persons: Dict[int, Dict] = {}  # {person_id: detection_data}
analysis_in_progress = False
current_analytics_data = {}
last_occupancy_log_time = datetime.utcnow()
last_heatmap_save_time = datetime.utcnow()


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    init_db()
    print("Database initialized")

    # Create directories
    for dir_path in ["uploads/frames", "uploads/thumbnails", "temp_videos",
                     "static", "heatmaps"]:
        os.makedirs(dir_path, exist_ok=True)

    # Initialize database with default zones and lines
    db = next(get_db())
    create_default_zones(db)
    create_default_lines(db)

    # Load zones and virtual lines
    zone_detector.load_zones(db)
    occupancy_counter.zone_detector = zone_detector
    line_crossing_detector.load_lines(db)

    # Load known faces
    face_detector.load_known_faces_from_db(db)

    # Start camera
    camera.start()

    # Register frame callback for detection
    camera.register_frame_callback(process_frame_with_analytics)

    print("Retail Analytics System started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    camera.stop()


def process_frame_with_analytics(frame):
    """
    Process each camera frame with hybrid person+face detection and retail analytics
    """
    global current_detected_persons, current_analytics_data
    global last_occupancy_log_time, last_heatmap_save_time

    timestamp = datetime.utcnow()
    frame_height, frame_width = frame.shape[:2]

    # Step 1: Detect persons for coarse segmentation
    person_detections = person_detector.detect_persons(frame)

    current_detections = {}
    detection_positions = {}  # {person_id: (norm_x, norm_y)}
    face_recognized_persons = set()  # Track which persons have recognized faces

    db = next(get_db())

    # Step 2: For each detected person, check for visible faces and analytics
    person_id_counter = 0  # For anonymous persons

    for person_bbox, person_confidence in person_detections:
        person_left, person_top, person_right, person_bottom = person_bbox

        # Calculate person centroid for trajectory tracking
        person_centroid_x = (person_left + person_right) / 2
        person_centroid_y = (person_top + person_bottom) / 2
        norm_x = person_centroid_x / frame_width
        norm_y = person_centroid_y / frame_height

        # Try face detection within person ROI
        roi_frame, offset_xy = person_detector.extract_person_roi(frame, person_bbox, padding=5)
        detected_faces_in_roi = face_detector.detect_faces_in_roi(frame, person_bbox, offset_xy)

        # Check which faces are sufficiently visible
        visible_faces = []
        for face_encoding, face_location in detected_faces_in_roi:
            if person_detector.is_face_visible(person_bbox, face_location, face_confidence):
                visible_faces.append((face_encoding, face_location))

        person_id = None
        person_name = f"Person_{person_id_counter}"
        face_visible = len(visible_faces) > 0
        is_new_person = False

        # Step 3: Try to recognize face if visible
        if face_visible:
            # Use the most confident face detection
            best_face_encoding, best_face_location = visible_faces[0]

            # Try to recognize face
            recognized_person_id = face_detector.recognize_face(best_face_encoding)

            if recognized_person_id:
                # Known person
                person = db.query(Person).filter(Person.id == recognized_person_id).first()
                if person:
                    face_detector.update_person_visit(db, recognized_person_id)
                    person_id = recognized_person_id
                    person_name = person.name

                    # Log detection event
                    frame_path = camera.save_frame(frame)
                    event = face_detector.log_detection_event(db, person_id, 0.95, frame_path)
                    face_recognized_persons.add(person_id)
            else:
                # New person - add to database
                person = face_detector.add_person_to_db(
                    db, best_face_encoding, frame, best_face_location
                )
                person_id = person.id
                person_name = person.name
                is_new_person = True

                # Log detection event
                frame_path = camera.save_frame(frame)
                event = face_detector.log_detection_event(db, person_id, 0.90, frame_path)
                face_recognized_persons.add(person_id)
        else:
            # No face visible - create/use anonymous tracking
            # For trajectory purposes, we'll use a temporary ID based on position
            # This person will be tracked but not added to the database permanently
            person_id = f"anon_{person_id_counter}"
            person_name = "Anonymous"

        # Step 4: Track trajectory using person centroid (regardless of face visibility)
        if face_visible:
            # Use face location for more precise trajectory when face is visible
            face_top, face_right, face_bottom, face_left = best_face_location
            face_centroid_x = (face_left + face_right) / 2
            face_centroid_y = (face_top + face_bottom) / 2
            trajectory_norm_x, trajectory_norm_y = trajectory_tracker.update_position(
                person_id, best_face_location, timestamp, frame_width, frame_height
            )
        else:
            # Use person bbox center for trajectory tracking
            # Create a pseudo-bbox around centroid for trajectory tracking
            pseudo_bbox = (
                int(person_centroid_y),  # top
                int(person_centroid_x + 10),  # right (small offset)
                int(person_centroid_y + 10),  # bottom (small offset)
                int(person_centroid_x)  # left
            )
            trajectory_norm_x, trajectory_norm_y = trajectory_tracker.update_position(
                person_id, pseudo_bbox, timestamp, frame_width, frame_height
            )

        detection_positions[person_id] = (trajectory_norm_x, trajectory_norm_y)

        # Step 5: Zone detection and analytics
        current_zone_id = zone_detector.find_zone((trajectory_norm_x, trajectory_norm_y))

        # Calculate dwell time
        dwell_time = dwell_calculator.update(
            person_id, current_zone_id, (trajectory_norm_x, trajectory_norm_y), timestamp
        )

        # Check line crossing
        crossing_event = line_crossing_detector.check_crossing(
            person_id, (trajectory_norm_x, trajectory_norm_y), timestamp
        )
        if crossing_event:
            # Only log crossings for recognized persons
            if person_id in face_recognized_persons:
                line_crossing_detector.log_crossing(db, int(person_id), crossing_event, timestamp)

        # Add to heatmap
        heatmap_generator.add_detection((trajectory_norm_x, trajectory_norm_y), weight=1.0)

        # Store current detection
        current_detections[person_id] = {
            'id': person_id if isinstance(person_id, int) else None,
            'name': person_name,
            'bbox': person_bbox,  # Use person bbox, not face bbox
            'zone_id': current_zone_id,
            'dwell_time': dwell_time,
            'position': (trajectory_norm_x, trajectory_norm_y),
            'face_visible': face_visible,
            'person_confidence': person_confidence
        }

        person_id_counter += 1

    # Step 6: Update occupancy
    occupancy_counts = occupancy_counter.update(detection_positions, timestamp)

    # Log occupancy every 5 minutes
    if (timestamp - last_occupancy_log_time).total_seconds() > 300:
        occupancy_counter.log_to_db(next(get_db()), timestamp)
        last_occupancy_log_time = timestamp

    # Step 3: Detect queues
    queues = queue_detector.detect_queues(detection_positions, zone_detector)
    for queue_data in queues:
        queue_detector.log_queue_metrics(next(get_db()), queue_data, timestamp)

    # Step 4: Save heatmap every hour
    if (timestamp - last_heatmap_save_time).total_seconds() > 3600:
        time_bucket = timestamp.strftime("%Y-%m-%d_%H:00")
        heatmap_generator.save_to_db(next(get_db()), time_bucket)
        last_heatmap_save_time = timestamp

    # Step 5: Build analytics data for overlay
    current_analytics_data = {
        'detections': [
            (d['id'], d['bbox'], d['name'], d['zone_id'], d['dwell_time'])
            for d in current_detections.values()
        ],
        'trajectories': {
            pid: trajectory_tracker.get_path(pid)
            for pid in current_detections.keys()
        },
        'zones': [
            {
                'id': zone['id'],
                'name': zone['name'],
                'polygon': zone['polygon'],
                'color': zone['color'],
                'occupancy': occupancy_counts.get(zone['id'], 0)
            }
            for zone in zone_detector.get_zones()
        ],
        'virtual_lines': [
            {
                'id': line['id'],
                'name': line['name'],
                'start': line['start'],
                'end': line['end'],
                'counts': line_crossing_detector.get_counts(line['id']),
                'color': line['color']
            }
            for line in line_crossing_detector.lines
        ],
        'queues': queues,
        'heatmap': heatmap_generator.generate_heatmap_overlay(alpha=0.5),
        'total_occupancy': occupancy_counts.get(None, 0),
        'active_trajectories': len(current_detections),
        'alerts': generate_alerts(occupancy_counts, queues)
    }

    current_detected_persons = current_detections

    # Broadcast analytics to connected clients
    asyncio.run(broadcast_analytics(current_analytics_data))

    # Trigger analysis for new face-recognized detections only
    for person_id, data in current_detections.items():
        if (isinstance(person_id, int) and  # Only for actual person IDs, not anonymous
            (person_id not in current_detected_persons or data.get('is_new'))):
            if not analysis_in_progress:
                threading.Thread(
                    target=trigger_retail_analysis,
                    args=(person_id, data.get('zone_id')),
                    daemon=True
                ).start()


def generate_alerts(occupancy_counts: Dict, queues: List[Dict]) -> List[Dict]:
    """Generate alerts based on analytics"""
    alerts = []

    # Queue alerts
    for queue in queues:
        if queue['length'] >= 5:
            alerts.append({
                'type': 'queue',
                'message': f"Queue Alert: {queue['length']} people waiting"
            })

    # Capacity alerts
    for zone in zone_detector.get_zones():
        if zone.get('max_capacity'):
            current_count = occupancy_counts.get(zone['id'], 0)
            if current_count > zone['max_capacity'] * 0.8:
                alerts.append({
                    'type': 'capacity',
                    'message': f"{zone['name']}: {current_count}/{zone['max_capacity']}"
                })

    return alerts


def trigger_retail_analysis(person_id: int, zone_id: Optional[int]):
    """Trigger retail-specific Gemini analysis"""
    global analysis_in_progress

    try:
        analysis_in_progress = True

        # Record clip
        print(f"Recording clip for person {person_id}...")
        video_path = camera.record_clip(duration=10)

        # Determine analysis type based on zone
        db = next(get_db())

        if zone_id:
            zone = db.query(Zone).filter(Zone.id == zone_id).first()
            zone_type = zone.zone_type if zone else None

            if zone_type == "queue":
                analysis_result = gemini_analyzer.analyze_queue_experience(video_path)
                analysis_type = "queue_experience"
            elif zone_type == "product":
                analysis_result = gemini_analyzer.analyze_product_interaction(
                    video_path, zone.name
                )
                analysis_type = "product_interaction"
            else:
                analysis_result = gemini_analyzer.analyze_shopping_behavior(video_path)
                analysis_type = "shopping_behavior"
        else:
            analysis_result = gemini_analyzer.analyze_shopping_behavior(video_path)
            analysis_type = "shopping_behavior"

        # Save to database
        gemini_analyzer.save_analysis_to_db(
            db,
            person_id,
            0,  # event_id placeholder
            analysis_type,
            list(analysis_result.values())[0],  # Get first value from dict
            video_path
        )

        # Broadcast analysis
        asyncio.run(broadcast_analysis({
            "person_id": person_id,
            "analysis_type": analysis_type,
            "analysis": list(analysis_result.values())[0],
            "timestamp": datetime.utcnow().isoformat()
        }))

    except Exception as e:
        print(f"Error in retail analysis: {e}")
    finally:
        analysis_in_progress = False


async def broadcast_analytics(data: dict):
    """Broadcast analytics data to all connected websockets"""
    # Simplify data for JSON serialization
    simplified_data = {
        'detections_count': len(data.get('detections', [])),
        'total_occupancy': data.get('total_occupancy', 0),
        'active_trajectories': data.get('active_trajectories', 0),
        'zones': data.get('zones', []),
        'virtual_lines': data.get('virtual_lines', []),
        'queues': data.get('queues', []),
        'alerts': data.get('alerts', [])
    }

    message = json.dumps({"type": "analytics", "data": simplified_data})
    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)

    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


async def broadcast_analysis(data: dict):
    """Broadcast Gemini analysis to dashboard"""
    message = json.dumps({"type": "analysis", "data": data})
    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)

    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/video_feed")
async def video_feed():
    """Stream live video feed with overlays"""
    def generate():
        while True:
            frame = camera.get_current_frame()
            if frame is not None and current_analytics_data:
                # Render overlays
                frame_with_overlays = overlay_renderer.render_frame(
                    frame,
                    current_analytics_data
                )
                # Encode frame
                jpg_bytes = camera.encode_frame_to_jpg(frame_with_overlays)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/analytics/current")
async def get_current_analytics():
    """Get current real-time analytics"""
    return {
        'occupancy': occupancy_counter.get_occupancy(None),
        'zones': [
            {
                'id': zone['id'],
                'name': zone['name'],
                'occupancy': occupancy_counter.get_occupancy(zone['id'])
            }
            for zone in zone_detector.get_zones()
        ],
        'detections': len(current_detected_persons),
        'alerts': current_analytics_data.get('alerts', [])
    }


@app.get("/api/heatmap/current")
async def get_current_heatmap():
    """Get current heatmap overlay as base64 image"""
    import base64
    heatmap_img = heatmap_generator.generate_heatmap_overlay()
    _, buffer = cv2.imencode('.png', heatmap_img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return {"heatmap": img_base64}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve retail analytics dashboard"""
    with open("static/retail_dashboard.html", "r") as f:
        return f.read()


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
