from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
import asyncio
import json
import cv2
import os
from typing import List
from datetime import datetime
import threading

from camera_manager import CameraManager
from person_detector import PersonDetector
from gemini_analyzer import GeminiAnalyzer
from activity_logger import activity_logger, analysis_streamer, log_activity, stream_analysis
from video_overlay import VideoOverlayRenderer
from retail_analytics import (
    TrajectoryTracker, DwellTimeCalculator, ZoneDetector,
    OccupancyCounter, LineCrossingDetector, HeatmapGenerator, QueueDetector
)
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Agent import AlertGenerator, AlertManager

# Import RAG system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.rag_api import create_rag_router

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Video AI Surveillance System")

# Add RAG router
rag_router = create_rag_router()
app.include_router(rag_router)

# Initialize components
camera = CameraManager(camera_source="https://www.youtube.com/watch?v=KMJS66jBtVQ")
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

# Initialize Alert System
alert_generator = AlertGenerator(api_key=os.getenv("GEMINI_API_KEY"))
alert_manager = AlertManager(max_queue_size=50, alert_expiry_seconds=600)

# WebSocket connections
active_connections: List[WebSocket] = []
metrics_connections: List[WebSocket] = []
alert_connections: List[WebSocket] = []

# Global state
current_detected_person = None
analysis_in_progress = False
current_detections = []
active_persons = {}  # person_id -> data
zones_data = []
lines_data = []
total_entries_today = 0  # Track entries in memory
current_metrics = {
    "occupancy": 0,
    "peak_today": 0,
    "avg_dwell_time": 0,
    "active_trajectories": 0,
    "total_entries": 0,
    "active_zones": 0
}


def initialize_zones_with_gemini():
    """Use Gemini to analyze video and generate zones/virtual lines"""
    try:
        import time
        import traceback

        log_activity("📹 Analyzing video for zone generation...", "system")

        # Wait for camera to stabilize
        time.sleep(2)

        # Get YouTube URL if available
        youtube_url = camera.camera_source if "youtube.com" in camera.camera_source or "youtu.be" in camera.camera_source else None
        
        if not youtube_url:
            log_activity("❌ No YouTube URL found - cannot generate zones", "system")
            return

        # Analyze video to generate zones and lines
        log_activity(f"🤖 Gemini analyzing video layout from: {youtube_url[:50]}...", "system")
        
        result = gemini_analyzer.analyze_layout_and_generate_zones(
            video_path=None,
            youtube_url=youtube_url
        )

        # Verbose logging of Gemini response
        if "error" in result:
            log_activity(f"❌ Gemini zone generation failed: {result['error']}", "system")
            print(f"ERROR DETAILS: {result}")
            if "raw_response" in result:
                print(f"RAW GEMINI RESPONSE:\n{result['raw_response']}")
            return

        log_activity(f"✅ Gemini returned {len(result.get('zones', []))} zones and {len(result.get('virtual_lines', []))} lines", "system")

        # Store zones and lines in memory
        global zones_data, lines_data
        zones_data = []
        lines_data = []
        zones_created = 0
        lines_created = 0

        for idx, zone_config in enumerate(result.get("zones", [])):
            try:
                zone_dict = {
                    "id": idx + 1,
                    "name": zone_config["name"],
                    "type": zone_config["zone_type"],
                    "polygon": zone_config["polygon_points"],
                    "color": zone_config.get("color", "#00FF00"),
                    "max_capacity": zone_config.get("max_capacity", 10),
                    "description": zone_config.get("description", ""),
                    "is_active": True
                }
                zones_data.append(zone_dict)
                zone_detector.zones.append(zone_dict)
                zones_created += 1
                log_activity(f"  ✓ Zone created: {zone_config['name']} ({zone_config['zone_type']})", "system")
            except Exception as ze:
                log_activity(f"  ❌ Failed to create zone: {str(ze)}", "system")
                print(f"Zone error: {ze}, Config: {zone_config}")

        for idx, line_config in enumerate(result.get("virtual_lines", [])):
            try:
                line_dict = {
                    "id": idx + 1,
                    "name": line_config["name"],
                    "start": line_config["start_point"],
                    "end": line_config["end_point"],
                    "count_direction": line_config.get("count_direction", "both"),
                    "color": line_config.get("color", "#FF0000"),
                    "description": line_config.get("description", ""),
                    "is_active": True
                }
                lines_data.append(line_dict)
                line_crossing_detector.lines.append(line_dict)
                line_crossing_detector.crossing_counts[idx + 1] = {"in": 0, "out": 0, "total": 0}
                lines_created += 1
                log_activity(f"  ✓ Line created: {line_config['name']}", "system")
            except Exception as le:
                log_activity(f"  ❌ Failed to create line: {str(le)}", "system")
                print(f"Line error: {le}, Config: {line_config}")

        occupancy_counter.zone_detector = zone_detector
        log_activity(f"✅ Gemini created {zones_created} zones and {lines_created} virtual lines - Now active!", "system")

    except Exception as e:
        error_details = traceback.format_exc()
        log_activity(f"❌ Error in Gemini zone initialization: {str(e)}", "system")
        print(f"FULL ERROR TRACEBACK:\n{error_details}")


def continuous_gemini_analysis_and_alerts():
    """Continuously analyze video with Gemini and generate alerts every 5 seconds"""
    try:
        import time

        log_activity("🤖 Gemini analysis + alert system started", "system")

        # Wait for system to stabilize
        time.sleep(5)

        frame_analysis_interval = 5  # Analyze every 5 seconds
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

                analysis_text = None
                if "error" not in analysis_result:
                    analysis_text = analysis_result.get("frame_analysis", "")

                    # Stream the full analysis
                    timestamp_str = datetime.utcnow().strftime('%H:%M:%S')
                    full_analysis = f"[{timestamp_str}] {analysis_text}"
                    stream_analysis(full_analysis, is_complete=True)

                    # Also log to activity feed
                    log_activity(f"📊 Gemini: {analysis_text[:100]}...", "analysis")

                # === INTEGRATED ALERT GENERATION ===
                # Prepare comprehensive analytics data
                analytics_data = {
                    'total_occupancy': current_metrics.get('occupancy', 0),
                    'occupancy': [],
                    'dwell_times': [],
                    'queue_metrics': []
                }
                
                # Add zone occupancy data
                for zone in zones_data:
                    zone_id = zone.get('id')
                    if zone_id:
                        zone_occupancy = occupancy_counter.get_occupancy(zone_id)
                        analytics_data['occupancy'].append({
                            'zone_id': zone_id,
                            'zone_name': zone.get('name', f'Zone {zone_id}'),
                            'current': zone_occupancy,
                            'capacity': zone.get('max_capacity', 0)
                        })
                
                # Add dwell time data
                for (person_id, zone_id), entry_data in dwell_calculator.zone_entries.items():
                    zone_name = next((z['name'] for z in zones_data if z.get('id') == zone_id), f'Zone {zone_id}')
                    zone_type = next((z['type'] for z in zones_data if z.get('id') == zone_id), 'product')
                    dwell_time = (datetime.utcnow() - entry_data['entry_time']).total_seconds()
                    
                    analytics_data['dwell_times'].append({
                        'person_id': person_id,
                        'zone_id': zone_id,
                        'zone_name': zone_name,
                        'zone_type': zone_type,
                        'duration': dwell_time
                    })
                
                # Create timestamp-specific data package
                timestamp_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'frame_time': timestamp_str,
                    'detections': len(current_detections),
                    'active_persons': list(occupancy_counter.current_occupancy.get(None, set())),
                    'zones_snapshot': analytics_data['occupancy'].copy(),
                    'gemini_analysis': analysis_text
                }
                
                # Generate alerts with combined data
                alerts = alert_generator.analyze_and_generate_alerts(
                    analytics_data=analytics_data,
                    behavior_analysis=analysis_text,
                    timestamp_data=timestamp_data
                )
                
                # Add alerts to manager
                added_alerts = alert_manager.add_alerts(alerts)
                
                # Broadcast new alerts
                if added_alerts:
                    log_activity(f"🚨 Generated {len(added_alerts)} new alert(s)", "system")
                    asyncio.run(broadcast_alert_update())

                # Clean up temporary file
                try:
                    os.remove(frame_path)
                except:
                    pass

                last_analysis_time = current_time

            time.sleep(1)

    except Exception as e:
        log_activity(f"❌ Error in continuous analysis: {str(e)}", "system")
        print(f"Error in continuous_gemini_analysis_and_alerts: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    log_activity("🎬 System initializing...", "system")

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

    # Initialize retail analytics
    log_activity("🏪 Initializing retail analytics...", "system")
    occupancy_counter.zone_detector = zone_detector

    global zones_data, lines_data
    zones_data = zone_detector.zones
    lines_data = line_crossing_detector.lines

    # Always use Gemini to analyze video and generate zones/lines
    log_activity("🤖 Using Gemini AI to analyze video layout...", "system")
    print("DEBUG: Starting Gemini zone generation thread...")
    threading.Thread(target=initialize_zones_with_gemini, daemon=True).start()
    print("DEBUG: Thread started")

    # Register frame callback for detection
    camera.register_frame_callback(process_frame)
    log_activity("✓ System ready - Real-time detection active", "system")

    # Start integrated Gemini analysis + alert generation (every 5 seconds)
    threading.Thread(target=continuous_gemini_analysis_and_alerts, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    camera.stop()


def process_frame(frame):
    """Process each camera frame for person detection and analytics"""
    global current_detected_person, analysis_in_progress, current_detections, current_metrics, total_entries_today

    try:
        # Detect persons
        person_detections = person_detector.detect_persons(frame)

        if len(person_detections) > 0:
            log_activity(f"🔍 Detected {len(person_detections)} person(s) in frame", "detection")

        # Update retail analytics for all detected persons
        global active_persons, zones_data
        frame_height, frame_width = frame.shape[:2]

        # Clear previous detections
        current_detections.clear()

        # Build positions dictionary for all detected persons
        person_positions = {}
        person_info_map = {}
        
        # Track all persons
        for idx, (person_bbox, person_confidence) in enumerate(person_detections):
            # Calculate normalized center position
            left, top, right, bottom = person_bbox
            center_x = (left + right) / 2 / frame_width
            center_y = (top + bottom) / 2 / frame_height

            # Generate person ID from bbox
            person_id = hash(str(person_bbox))
            person_name = f"Person {idx + 1}"

            # Store position for occupancy counter
            person_positions[person_id] = (center_x, center_y)
            
            # Store person info
            person_info_map[person_id] = {
                "name": person_name,
                "bbox": person_bbox,
                "confidence": person_confidence
            }

            # Update trajectory
            current_zone_id = zone_detector.find_zone((center_x, center_y))
            trajectory_tracker.update_position(
                person_id,
                person_bbox,
                datetime.utcnow(),
                frame_width,
                frame_height,
                current_zone_id
            )

            # Update heatmap
            heatmap_generator.add_detection((center_x, center_y))

            # Update dwell time
            if current_zone_id:
                dwell_calculator.update(
                    person_id,
                    current_zone_id,
                    (center_x, center_y),
                    datetime.utcnow()
                )

            # Check line crossings
            line_crossing_detector.check_crossing(person_id, (center_x, center_y), datetime.utcnow())

        # Update occupancy counter with all positions
        zone_occupancies = occupancy_counter.update(person_positions, datetime.utcnow())

        # Build current_detections for overlay rendering
        for person_id, position in person_positions.items():
            zone_id = zone_detector.find_zone(position)
            
            # Get dwell time for this person in their zone
            dwell_time = dwell_calculator.get_current_dwell_time(person_id, zone_id) if zone_id else None

            # Get person info
            info = person_info_map.get(person_id, {"name": "Person", "bbox": (0, 0, 0, 0)})
            person_bbox = info["bbox"]
            person_name = info["name"]

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

        # Update metrics - Current customers is the number of people detected
        current_metrics["occupancy"] = len(person_positions)
        current_metrics["active_zones"] = len(zone_detector.zones)
        current_metrics["active_trajectories"] = len(trajectory_tracker.active_trajectories)
        
        # Calculate average dwell time across all persons in zones
        dwell_times = []
        for person_id in person_positions.keys():
            for zone in zones_data:
                zone_id = zone.get('id')
                if zone_id:
                    dwell_time = dwell_calculator.get_current_dwell_time(person_id, zone_id)
                    if dwell_time and dwell_time > 0:
                        dwell_times.append(dwell_time)
        
        current_metrics["avg_dwell_time"] = sum(dwell_times) / len(dwell_times) if dwell_times else 0
        
        # Track entries in memory (count unique person detections)
        if len(person_positions) > 0:
            total_entries_today += 1
            current_metrics["total_entries"] = total_entries_today

        if current_metrics["occupancy"] > current_metrics["peak_today"]:
            current_metrics["peak_today"] = current_metrics["occupancy"]

        # Broadcast metrics
        asyncio.run(broadcast_metrics())

    except Exception as e:
        print(f"Error in process_frame: {e}")
        import traceback
        traceback.print_exc()


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


async def broadcast_alert_update():
    """Broadcast alert updates to all connected websockets"""
    disconnected = []
    alerts = alert_manager.get_alerts_for_dashboard()

    for connection in alert_connections:
        try:
            await connection.send_json({"type": "alerts", "data": alerts})
        except:
            disconnected.append(connection)

    for conn in disconnected:
        alert_connections.remove(conn)




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


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts"""
    await websocket.accept()
    alert_connections.append(websocket)
    
    try:
        # Send current alerts on connect
        alerts = alert_manager.get_alerts_for_dashboard()
        await websocket.send_json({"type": "alerts", "data": alerts})
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in alert_connections:
            alert_connections.remove(websocket)


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

                # Format zones for display with actual occupancy
                zones_for_display = []
                for zone in zones_data:
                    # Get actual occupancy for this zone from occupancy_counter
                    zone_id = zone.get('id')
                    zone_occupancy = occupancy_counter.get_occupancy(zone_id)
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


@app.get("/api/current_detection")
async def get_current_detection():
    """Get currently detected person"""
    return current_detected_person or {"message": "No person detected"}


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


@app.get("/api/alerts")
async def get_alerts(recipient: str = None):
    """Get active alerts with optional recipient filter"""
    from Agent.alert_types import AlertRecipient
    
    recipient_filter = None
    if recipient:
        try:
            recipient_filter = AlertRecipient(recipient.lower())
        except ValueError:
            pass
    
    alerts = alert_manager.get_active_alerts(recipient_filter=recipient_filter)
    return [alert.to_dict() for alert in alerts]


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    success = alert_manager.acknowledge_alert(alert_id)
    if success:
        await broadcast_alert_update()
    return {"success": success}


@app.post("/api/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str):
    """Dismiss an alert"""
    success = alert_manager.dismiss_alert(alert_id)
    if success:
        await broadcast_alert_update()
    return {"success": success}


@app.get("/api/alerts/statistics")
async def get_alert_statistics():
    """Get alert statistics"""
    return alert_manager.get_alert_statistics()


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
