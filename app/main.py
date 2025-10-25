from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json
import cv2
import os
from typing import List
from datetime import datetime
import threading

from database import init_db, get_db, Person, DetectionEvent, BehaviorAnalysis
from camera_manager import CameraManager
from face_detector import FaceDetector
from person_detector import PersonDetector
from gemini_analyzer import GeminiAnalyzer
from activity_logger import activity_logger, analysis_streamer, log_activity, stream_analysis
from video_overlay import VideoOverlayRenderer
from retail_analytics import (
    TrajectoryTracker, DwellTimeCalculator, ZoneDetector,
    OccupancyCounter, LineCrossingDetector, HeatmapGenerator, QueueDetector
)
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Video AI Surveillance System")

# Initialize components
camera = CameraManager(camera_source="https://www.youtube.com/watch?v=KMJS66jBtVQ")
face_detector = FaceDetector(tolerance=0.6)
person_detector = PersonDetector(confidence_threshold=0.7)
gemini_analyzer = GeminiAnalyzer(api_key=os.getenv("GEMINI_API_KEY"))
video_overlay = VideoOverlayRenderer(width=1280, height=720)

# Initialize retail analytics components
trajectory_tracker = TrajectoryTracker(history_duration_seconds=60)
dwell_calculator = DwellTimeCalculator()
zone_detector = ZoneDetector()
occupancy_counter = OccupancyCounter()
line_crossing_detector = LineCrossingDetector()
heatmap_generator = HeatmapGenerator(width=1280, height=720, resolution=20)
queue_detector = QueueDetector()

# WebSocket connections
active_connections: List[WebSocket] = []
metrics_connections: List[WebSocket] = []

# Global state
current_detected_person = None
analysis_in_progress = False
current_detections = []
active_persons = {}  # person_id -> data
zones_data = []
lines_data = []
current_metrics = {
    "occupancy": 0,
    "peak_today": 0,
    "detections_count": 0,
    "active_zones": 0
}


def initialize_zones_with_gemini():
    """Use Gemini to analyze first 5 seconds of video and generate zones/virtual lines"""
    try:
        import time
        from database import Zone, VirtualLine

        log_activity("📹 Capturing first 5 seconds of video for Gemini analysis...", "system")

        # Wait for camera to stabilize
        time.sleep(2)

        # Get YouTube URL if available
        youtube_url = camera.camera_source if "youtube.com" in camera.camera_source or "youtu.be" in camera.camera_source else None

        # Analyze video to generate zones and lines
        log_activity("🤖 Gemini analyzing video layout...", "system")
        result = gemini_analyzer.analyze_layout_and_generate_zones(
            video_path=None,
            youtube_url=youtube_url
        )

        if "error" in result:
            log_activity(f"❌ Gemini zone generation failed: {result['error']}", "system")
            return

        # Save zones to database
        db = next(get_db())
        zones_created = 0
        lines_created = 0

        for zone_config in result.get("zones", []):
            zone = Zone(
                name=zone_config["name"],
                zone_type=zone_config["zone_type"],
                polygon_points=json.dumps(zone_config["polygon_points"]),
                color=zone_config.get("color", "#00FF00"),
                max_capacity=zone_config.get("max_capacity", 10),
                description=zone_config.get("description", ""),
                is_active=True
            )
            db.add(zone)
            zones_created += 1

        for line_config in result.get("virtual_lines", []):
            vline = VirtualLine(
                name=line_config["name"],
                start_x=line_config["start_point"]["x"],
                start_y=line_config["start_point"]["y"],
                end_x=line_config["end_point"]["x"],
                end_y=line_config["end_point"]["y"],
                count_direction=line_config.get("count_direction", "both"),
                color=line_config.get("color", "#FF0000"),
                description=line_config.get("description", ""),
                is_active=True
            )
            db.add(vline)
            lines_created += 1

        db.commit()

        # Reload zones and lines into detectors
        zone_detector.load_zones(db)
        line_crossing_detector.load_lines(db)

        global zones_data, lines_data
        zones_data = zone_detector.get_zones()
        lines_data = line_crossing_detector.lines

        log_activity(f"✅ Gemini created {zones_created} zones and {lines_created} virtual lines", "system")

    except Exception as e:
        log_activity(f"❌ Error in Gemini zone initialization: {str(e)}", "system")
        print(f"Error in initialize_zones_with_gemini: {e}")


def continuous_gemini_analysis():
    """Continuously analyze video and stream analysis to dashboard"""
    try:
        import time

        log_activity("🤖 Gemini continuous analysis started", "system")

        # Wait for system to stabilize
        time.sleep(5)

        frame_analysis_interval = 10  # Analyze every 10 seconds
        last_analysis_time = 0

        while True:
            current_time = time.time()

            if current_time - last_analysis_time >= frame_analysis_interval:
                # Get current frame
                frame = camera.get_current_frame()
                if frame is None:
                    time.sleep(1)
                    continue

                # Save frame temporarily for analysis
                frame_path = f"data/temp_videos/gemini_analysis_frame_{int(current_time)}.jpg"
                cv2.imwrite(frame_path, frame)

                # Stream analysis start
                stream_analysis(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Analyzing current scene...", is_complete=False)

                # Analyze frame with Gemini
                analysis_result = gemini_analyzer.analyze_single_frame(frame_path)

                if "error" not in analysis_result:
                    analysis_text = analysis_result.get("frame_analysis", "")

                    # Stream the full analysis
                    timestamp_str = datetime.utcnow().strftime('%H:%M:%S')
                    full_analysis = f"[{timestamp_str}] {analysis_text}"
                    stream_analysis(full_analysis, is_complete=True)

                    # Also log to activity feed
                    log_activity(f"📊 Gemini: {analysis_text[:100]}...", "analysis")

                # Clean up temporary file
                try:
                    os.remove(frame_path)
                except:
                    pass

                last_analysis_time = current_time

            time.sleep(1)

    except Exception as e:
        log_activity(f"❌ Error in continuous Gemini analysis: {str(e)}", "system")
        print(f"Error in continuous_gemini_analysis: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    log_activity("🎬 System initializing...", "system")

    init_db()
    log_activity("✓ Database initialized", "system")

    # Create directories
    os.makedirs("data/uploads/frames", exist_ok=True)
    os.makedirs("data/uploads/thumbnails", exist_ok=True)
    os.makedirs("data/temp_videos", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    log_activity("✓ Directories created", "system")

    # Start camera
    log_activity("🎥 Starting camera stream...", "system")
    camera.start()
    log_activity(f"✓ Camera active - {camera.camera_source}", "system")

    # Load known faces
    db = next(get_db())
    face_detector.load_known_faces_from_db(db)
    log_activity(f"✓ Loaded {len(face_detector.known_face_ids)} known faces", "system")

    # Initialize retail analytics
    log_activity("🏪 Initializing retail analytics...", "system")
    zone_detector.load_zones(db)
    occupancy_counter.zone_detector = zone_detector
    line_crossing_detector.load_lines(db)

    global zones_data, lines_data
    zones_data = zone_detector.get_zones()
    lines_data = line_crossing_detector.lines

    # If no zones/lines exist, use Gemini to analyze video and generate them
    if len(zones_data) == 0 and len(lines_data) == 0:
        log_activity("🤖 No zones/lines found - Using Gemini AI to analyze video layout...", "system")
        threading.Thread(target=initialize_zones_with_gemini, daemon=True).start()
    else:
        log_activity(f"✓ Loaded {len(zones_data)} zones and {len(lines_data)} virtual lines", "system")

    # Register frame callback for detection
    camera.register_frame_callback(process_frame)
    log_activity("✓ System ready - Real-time detection active", "system")

    # Start continuous Gemini analysis streaming
    threading.Thread(target=continuous_gemini_analysis, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    camera.stop()


def process_frame(frame):
    """Process each camera frame with hybrid person+face detection"""
    global current_detected_person, analysis_in_progress, current_detections, current_metrics

    try:
        # Step 1: Detect persons for coarse segmentation
        person_detections = person_detector.detect_persons(frame)

        if len(person_detections) > 0:
            log_activity(f"🔍 Detected {len(person_detections)} person(s) in frame", "detection")

        db = next(get_db())

        # Step 2: For each detected person, check for visible faces
        for person_bbox, person_confidence in person_detections:
            # Extract person ROI with padding for face detection
            roi_frame, offset_xy = person_detector.extract_person_roi(frame, person_bbox, padding=10)

            # Detect faces within the person ROI
            detected_faces_in_roi = face_detector.detect_faces_in_roi(frame, person_bbox, offset_xy)

            # Check if any faces are sufficiently visible
            visible_faces = []
            for detection_result in detected_faces_in_roi:
                try:
                    # Safely unpack face detection results
                    if len(detection_result) == 3:
                        face_encoding, face_location, face_confidence = detection_result
                        if person_detector.is_face_visible(person_bbox, face_location, face_confidence):
                            visible_faces.append((face_encoding, face_location))
                    else:
                        print(f"Warning: Unexpected face detection result format: {len(detection_result)} elements")
                except Exception as e:
                    print(f"Error processing face detection result: {e}")
                    continue

            face_recognized = False
            person_data = None

            # Step 3: Try to recognize face if visible
            if len(visible_faces) > 0:
                # Use the most confident face detection
                best_face_encoding, best_face_location = visible_faces[0]

                # Try to recognize face
                person_id = face_detector.recognize_face(best_face_encoding)

                if person_id:
                    # Known person detected
                    person = db.query(Person).filter(Person.id == person_id).first()
                    face_detector.update_person_visit(db, person_id)
                    face_recognized = True
                    log_activity(f"👤 Recognized: {person.name} (Visit #{person.visit_count})", "detection",
                               {"person_id": person_id, "visit_count": person.visit_count})
                else:
                    # Unknown person - add to database
                    log_activity("👤 New person detected - Adding to database", "detection")
                    person = face_detector.add_person_to_db(
                        db, best_face_encoding, frame, best_face_location
                    )
                    face_recognized = True
                    log_activity(f"✓ New person added: {person.name}", "detection", {"person_id": person.id})

                person_data = {
                    "id": person.id,
                    "name": person.name,
                    "visit_count": person.visit_count,
                    "first_seen": person.first_seen.isoformat(),
                    "last_seen": person.last_seen.isoformat(),
                    "thumbnail": person.thumbnail_path,
                    "is_new": not person_id,
                    "face_visible": True,
                    "person_confidence": person_confidence
                }
            else:
                # Person detected but no face visible - still track anonymously
                # Create or retrieve anonymous person record based on position/size heuristic
                # For now, we'll just log the detection without face recognition
                person_data = {
                    "name": "Person (Face Not Visible)",
                    "is_new": True,
                    "face_visible": False,
                    "person_confidence": person_confidence,
                    "bbox": person_bbox
                }

            # Step 4: Log detection and trigger analysis if face was recognized
            if face_recognized and person_data and person_data.get("id"):
                # Log detection event
                frame_path = camera.save_frame(frame)
                event = face_detector.log_detection_event(
                    db, person_data["id"], 0.95, frame_path
                )

                current_detected_person = person_data

                # Trigger behavior analysis
                if not analysis_in_progress:
                    threading.Thread(
                        target=trigger_behavior_analysis,
                        args=(person_data["id"], event.id),
                        daemon=True
                    ).start()

                # Broadcast to dashboard
                asyncio.run(broadcast_detection(current_detected_person))

        # Step 5: Update retail analytics for all detected persons
        global active_persons, current_metrics, zones_data
        frame_height, frame_width = frame.shape[:2]

        # Clear previous detections
        current_detections.clear()

        # Track all persons (both recognized and anonymous)
        for person_bbox, person_confidence in person_detections:
            # Calculate normalized center position
            center_x = (person_bbox[0] + person_bbox[2]) / 2 / frame_width
            center_y = (person_bbox[1] + person_bbox[3]) / 2 / frame_height

            # Get person ID (use bbox as temp ID if not recognized)
            person_id = person_data.get("id") if person_data and "id" in person_data else hash(str(person_bbox))

            # Update trajectory (needs bbox and timestamp)
            trajectory_tracker.update_position(
                person_id,
                person_bbox,
                datetime.utcnow(),
                frame_width,
                frame_height
            )

            # Update heatmap
            heatmap_generator.add_detection((center_x, center_y))

            # Check zone occupancy
            zone_id = zone_detector.find_zone((center_x, center_y))
            if zone_id:
                # Update occupancy counter
                occupancy_counter.update({person_id: zone_id})
                # Update dwell time
                dwell_calculator.update(person_id, zone_id)

            # Check line crossings
            line_crossing_detector.check_crossing(person_id, (center_x, center_y), datetime.utcnow())

            # Get dwell time for this person in their zone
            dwell_time = None
            if zone_id and person_id in dwell_calculator.dwell_times:
                zone_times = dwell_calculator.dwell_times[person_id]
                if zone_id in zone_times:
                    dwell_time = (datetime.utcnow() - zone_times[zone_id]).total_seconds()

            # Get person name if available
            person_name = person_data.get("name") if person_data else "Person"

            # Convert bbox from (left, top, right, bottom) to (top, right, bottom, left) for VideoOverlayRenderer
            left, top, right, bottom = person_bbox
            bbox_for_overlay = (top, right, bottom, left)

            # Add to current_detections in format: (person_id, bbox, name, zone_id, dwell_time)
            current_detections.append((
                person_id,
                bbox_for_overlay,
                person_name,
                zone_id,
                dwell_time
            ))

        # Update metrics
        occupancy = occupancy_counter.get_occupancy()
        current_metrics["occupancy"] = occupancy
        current_metrics["detections_count"] += len(person_detections)
        current_metrics["active_zones"] = len(zone_detector.zones)

        if occupancy > current_metrics["peak_today"]:
            current_metrics["peak_today"] = occupancy

        # Broadcast metrics
        asyncio.run(broadcast_metrics())

    except Exception as e:
        print(f"Error in process_frame: {e}")
        import traceback
        traceback.print_exc()


def trigger_behavior_analysis(person_id: int, event_id: int):
    """Trigger Gemini analysis for detected person"""
    global analysis_in_progress

    try:
        analysis_in_progress = True

        # Record 10-second clip
        log_activity("🎬 Recording 10-second clip for analysis...", "analysis")
        video_path = camera.record_clip(duration=10)
        log_activity(f"✓ Clip saved: {video_path}", "analysis")

        # Analyze with Gemini
        log_activity("🤖 Analyzing behavior with Gemini AI...", "analysis")
        stream_analysis("Uploading video clip to Gemini...", f"person_{person_id}", False)
        analysis_result = gemini_analyzer.analyze_behavior(video_path)

        # Stream the analysis text
        if "full_analysis" in analysis_result:
            analysis_text = analysis_result["full_analysis"]
            stream_analysis(analysis_text, f"person_{person_id}", True)
            log_activity("✓ Gemini analysis complete", "analysis")

        # Save to database
        db = next(get_db())
        gemini_analyzer.save_analysis_to_db(
            db,
            person_id,
            event_id,
            "full_behavior",
            analysis_result.get("full_analysis", ""),
            video_path
        )

        # Broadcast analysis to dashboard
        asyncio.run(broadcast_analysis({
            "person_id": person_id,
            "analysis": analysis_result.get("full_analysis", ""),
            "timestamp": datetime.utcnow().isoformat()
        }))

    except Exception as e:
        print(f"Error in behavior analysis: {e}")
    finally:
        analysis_in_progress = False


async def broadcast_detection(data: dict):
    """Broadcast person detection to all connected websockets"""
    message = json.dumps({"type": "detection", "data": data})
    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)

    for conn in disconnected:
        active_connections.remove(conn)


async def broadcast_analysis(data: dict):
    """Broadcast analysis results to all connected websockets"""
    message = json.dumps({"type": "analysis", "data": data})
    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_text(message)
        except:
            disconnected.append(connection)

    for conn in disconnected:
        active_connections.remove(conn)


async def broadcast_metrics():
    """Broadcast metrics to all connected websockets"""
    disconnected = []

    for connection in metrics_connections:
        try:
            await connection.send_json({"type": "metrics", "data": current_metrics})
        except:
            disconnected.append(connection)

    for conn in disconnected:
        metrics_connections.remove(conn)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


@app.websocket("/ws/activity")
async def websocket_activity(websocket: WebSocket):
    """WebSocket endpoint for system activity stream"""
    await activity_logger.connect(websocket)
    log_activity("📡 Dashboard connected - Activity stream active", "system")

    try:
        while True:
            # Keep connection alive and listen for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        activity_logger.disconnect(websocket)
        log_activity("📡 Dashboard disconnected", "system")


@app.websocket("/ws/analysis")
async def websocket_analysis(websocket: WebSocket):
    """WebSocket endpoint for Gemini analysis stream"""
    await analysis_streamer.connect(websocket)
    log_activity("🤖 Analysis stream connected", "system")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        analysis_streamer.disconnect(websocket)


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for live metrics"""
    await websocket.accept()
    metrics_connections.append(websocket)

    try:
        # Send current metrics on connect
        await websocket.send_json({"type": "metrics", "data": current_metrics})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in metrics_connections:
            metrics_connections.remove(websocket)


@app.get("/video_feed")
async def video_feed():
    """Stream live video feed with overlays"""
    def generate():
        while True:
            frame = camera.get_current_frame()
            if frame is not None:
                # Get analytics data
                trajectories = trajectory_tracker.active_trajectories
                heatmap = heatmap_generator.generate_heatmap_overlay()

                # Format zones for display
                zones_for_display = []
                for zone in zones_data:
                    # Get occupancy for this zone (zone_detector.zones is a dict)
                    zone_occupancy = 0  # Default
                    zones_for_display.append({
                        **zone,
                        "occupancy": zone_occupancy
                    })

                # Format lines for display with counts
                lines_for_display = []
                for line in lines_data:
                    line_id = line.get("id", 0)
                    counts = line_crossing_detector.get_counts(line_id) if line_id in line_crossing_detector.crossing_counts else {"in": 0, "out": 0}
                    lines_for_display.append({
                        **line,
                        "counts": counts
                    })

                # Apply overlays
                analytics_data = {
                    "detections": current_detections,
                    "zones": zones_for_display,
                    "virtual_lines": lines_for_display,
                    "trajectories": trajectories,
                    "heatmap": heatmap,
                    "total_occupancy": current_metrics.get("occupancy", 0),
                    "active_trajectories": len(trajectories)
                }

                frame_with_overlays = video_overlay.render_frame(frame, analytics_data)

                # Encode frame
                jpg_bytes = camera.encode_frame_to_jpg(frame_with_overlays)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/persons")
async def get_all_persons(db: Session = Depends(get_db)):
    """Get all persons from database"""
    persons = db.query(Person).all()
    return [{
        "id": p.id,
        "name": p.name,
        "visit_count": p.visit_count,
        "first_seen": p.first_seen.isoformat(),
        "last_seen": p.last_seen.isoformat(),
        "thumbnail": p.thumbnail_path
    } for p in persons]


@app.get("/api/person/{person_id}")
async def get_person(person_id: int, db: Session = Depends(get_db)):
    """Get person details"""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return {"error": "Person not found"}

    # Get recent analyses
    analyses = db.query(BehaviorAnalysis)\
        .filter(BehaviorAnalysis.person_id == person_id)\
        .order_by(BehaviorAnalysis.timestamp.desc())\
        .limit(5)\
        .all()

    return {
        "id": person.id,
        "name": person.name,
        "visit_count": person.visit_count,
        "first_seen": person.first_seen.isoformat(),
        "last_seen": person.last_seen.isoformat(),
        "thumbnail": person.thumbnail_path,
        "notes": person.notes,
        "recent_analyses": [{
            "type": a.analysis_type,
            "text": a.analysis_text,
            "timestamp": a.timestamp.isoformat()
        } for a in analyses]
    }


@app.get("/api/current_detection")
async def get_current_detection():
    """Get currently detected person"""
    return current_detected_person or {"message": "No person detected"}


@app.get("/api/analytics/overview")
async def get_analytics_overview(db: Session = Depends(get_db)):
    """Get overall analytics overview"""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Total persons
    total_persons = db.query(Person).count()
    
    # Total detection events
    total_detections = db.query(DetectionEvent).count()
    
    # Total behavior analyses
    total_analyses = db.query(BehaviorAnalysis).count()
    
    # Today's detections
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_detections = db.query(DetectionEvent)\
        .filter(DetectionEvent.timestamp >= today_start)\
        .count()
    
    # This week's detections
    week_start = datetime.utcnow() - timedelta(days=7)
    week_detections = db.query(DetectionEvent)\
        .filter(DetectionEvent.timestamp >= week_start)\
        .count()
    
    # Average visits per person
    avg_visits = db.query(func.avg(Person.visit_count)).scalar() or 0
    
    # Most frequent visitor
    most_frequent = db.query(Person)\
        .order_by(Person.visit_count.desc())\
        .first()
    
    most_frequent_data = None
    if most_frequent:
        most_frequent_data = {
            "id": most_frequent.id,
            "name": most_frequent.name,
            "visit_count": most_frequent.visit_count,
            "thumbnail": most_frequent.thumbnail_path
        }
    
    # Last detection time
    last_detection = db.query(DetectionEvent)\
        .order_by(DetectionEvent.timestamp.desc())\
        .first()
    
    last_detection_time = None
    if last_detection:
        last_detection_time = last_detection.timestamp.isoformat()
    
    return {
        "total_persons": total_persons,
        "total_detections": total_detections,
        "total_analyses": total_analyses,
        "today_detections": today_detections,
        "week_detections": week_detections,
        "avg_visits_per_person": round(avg_visits, 2),
        "most_frequent_visitor": most_frequent_data,
        "last_detection_time": last_detection_time
    }


@app.get("/api/analytics/recent_detections")
async def get_recent_detections(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent detection events"""
    detections = db.query(DetectionEvent)\
        .order_by(DetectionEvent.timestamp.desc())\
        .limit(limit)\
        .all()
    
    result = []
    for detection in detections:
        person = db.query(Person).filter(Person.id == detection.person_id).first()
        result.append({
            "id": detection.id,
            "person_id": detection.person_id,
            "person_name": person.name if person else "Unknown",
            "person_thumbnail": person.thumbnail_path if person else None,
            "timestamp": detection.timestamp.isoformat(),
            "confidence": detection.confidence,
            "frame_path": detection.frame_path
        })
    
    return result


@app.get("/api/analytics/timeline")
async def get_detection_timeline(hours: int = 24, db: Session = Depends(get_db)):
    """Get detection events timeline"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Group by hour
    detections = db.query(
        func.strftime('%Y-%m-%d %H:00:00', DetectionEvent.timestamp).label('hour'),
        func.count(DetectionEvent.id).label('count')
    ).filter(
        DetectionEvent.timestamp >= start_time
    ).group_by('hour').all()
    
    return [{
        "timestamp": hour,
        "count": count
    } for hour, count in detections]


@app.get("/api/analytics/behavior_summary")
async def get_behavior_summary(limit: int = 5, db: Session = Depends(get_db)):
    """Get recent behavior analyses"""
    analyses = db.query(BehaviorAnalysis)\
        .order_by(BehaviorAnalysis.timestamp.desc())\
        .limit(limit)\
        .all()
    
    result = []
    for analysis in analyses:
        person = db.query(Person).filter(Person.id == analysis.person_id).first()
        result.append({
            "id": analysis.id,
            "person_id": analysis.person_id,
            "person_name": person.name if person else "Unknown",
            "analysis_type": analysis.analysis_type,
            "analysis_text": analysis.analysis_text[:200] + "..." if len(analysis.analysis_text) > 200 else analysis.analysis_text,
            "timestamp": analysis.timestamp.isoformat(),
            "video_clip": analysis.video_clip_path
        })
    
    return result


@app.post("/api/overlay/toggle")
async def toggle_overlay(overlay_name: str, enabled: bool):
    """Toggle video overlay layer"""
    video_overlay.toggle_overlay(overlay_name, enabled)
    log_activity(f"⚙️ Overlay '{overlay_name}' {'enabled' if enabled else 'disabled'}", "system")
    return {"success": True, "overlay": overlay_name, "enabled": enabled}


@app.get("/api/overlay/settings")
async def get_overlay_settings():
    """Get current overlay settings"""
    return video_overlay.get_overlay_config()


@app.get("/api/activity/recent")
async def get_recent_activity(limit: int = 50):
    """Get recent activity logs"""
    return activity_logger.get_recent_activities(limit)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard HTML"""
    try:
        with open("static/dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to index.html if dashboard.html doesn't exist yet
        try:
            with open("static/index.html", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "<html><body><h1>Video AI Dashboard - Coming Soon</h1><p>Dashboard is being set up...</p></body></html>"


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
