from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import asyncio
import json
import cv2
import os
from typing import List, Optional
from datetime import datetime, UTC
import threading

from app.video import CameraManager, VideoOverlayRenderer
from app.detection import PersonDetector, InteractionDetector, GazeDetector
from app.analytics import GeminiAnalyzer
from app.analytics.retail_analytics import (
    TrajectoryTracker, DwellTimeCalculator, ZoneDetector,
    OccupancyCounter, LineCrossingDetector, HeatmapGenerator, QueueDetector, InteractionTracker
)
from app.utils import activity_logger, analysis_streamer, log_activity, stream_analysis
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Agent import AlertGenerator, AlertManager

# Import RAG system
from rag.rag_api import create_rag_router

# Import Staff Location Tracker
from app.tracking.staff_location_tracker import router as staff_location_router

# Import Merged Logs System
from merged_logs import init_merged_db, collect_analytics_snapshot, MergedLogger

# Import Product Inventory System
from app.inventory import ProductDetector, ProductInteractionTracker
from app.api.inventory_routes import router as inventory_router

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Video AI Surveillance System")

# Add RAG router
rag_router = create_rag_router()
app.include_router(rag_router)

# Add Staff Location Tracker router
app.include_router(staff_location_router)

# Add Product Inventory router
app.include_router(inventory_router)

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
interaction_tracker = InteractionTracker()

# Initialize Phase 2 & 3 components
interaction_detector = InteractionDetector(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    proximity_threshold=0.15
)
gaze_detector = GazeDetector(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    fixation_threshold_seconds=0.5
)

# Initialize Alert System
alert_generator = AlertGenerator(api_key=os.getenv("GEMINI_API_KEY"))
alert_manager = AlertManager(max_queue_size=50, alert_expiry_seconds=600)

# Initialize Merged Logs Logger
merged_logger = MergedLogger()

# Initialize Product Inventory System
product_detector = ProductDetector(gemini_analyzer)
product_interaction_tracker = ProductInteractionTracker(
    product_detector=product_detector,
    gaze_detector=gaze_detector,
    interaction_detector=interaction_detector
)

# WebSocket connections
active_connections: List[WebSocket] = []
metrics_connections: List[WebSocket] = []
alert_connections: List[WebSocket] = []
inventory_connections: List[WebSocket] = []
customer_connections: List[WebSocket] = []

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


def initialize_products_in_zones():
    """Use Gemini to detect and catalog products in product zones"""
    try:
        import time
        from app.core.database import SessionLocal

        log_activity("🛍️ Detecting products in zones...", "system")

        # Wait for zones to be created
        time.sleep(5)

        if not zones_data:
            log_activity("❌ No zones available for product detection", "system")
            return

        # Get current frame for analysis
        frame = camera.get_current_frame()
        if frame is None:
            log_activity("❌ No frame available for product detection", "system")
            return

        # Create database session
        db = SessionLocal()

        try:
            # Detect products in all product zones
            detected_products = product_detector.detect_products_in_zones(
                frame=frame,
                zones=zones_data,
                db=db
            )

            total_products = sum(len(products) for products in detected_products.values())

            if total_products > 0:
                log_activity(f"✅ Product detection complete: {total_products} products catalogued", "system")

                # Log product summary by zone
                for zone_id, products in detected_products.items():
                    zone_name = next((z['name'] for z in zones_data if z.get('id') == zone_id), f'Zone {zone_id}')
                    log_activity(f"  ✓ {zone_name}: {len(products)} products", "system")
            else:
                log_activity("⚠️ No products detected in zones", "system")

        except Exception as e:
            log_activity(f"❌ Error detecting products: {str(e)}", "system")
            print(f"Product detection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

    except Exception as e:
        log_activity(f"❌ Error in product initialization: {str(e)}", "system")
        print(f"Error in initialize_products_in_zones: {e}")
        import traceback
        traceback.print_exc()


def continuous_gemini_analysis_and_alerts():
    """Continuously analyze video with Gemini and generate alerts every 5 seconds"""
    try:
        import time

        log_activity("🤖 Gemini analysis + alert system started", "system")

        # Wait for system to stabilize
        time.sleep(5)

        frame_analysis_interval = 1  # Analyze every 1 second
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
                stream_analysis(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] Analyzing current scene...", is_complete=False)

                # Analyze frame with Gemini
                analysis_result = gemini_analyzer.analyze_single_frame(frame_path)

                analysis_text = None
                timestamp_str = datetime.now(UTC).strftime('%H:%M:%S')

                if "error" not in analysis_result:
                    analysis_text = analysis_result.get("frame_analysis", "")

                    # Stream the full analysis if we got valid text
                    if analysis_text:
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
                    dwell_time = (datetime.now(UTC) - entry_data['entry_time']).total_seconds()

                    analytics_data['dwell_times'].append({
                        'person_id': person_id,
                        'zone_id': zone_id,
                        'zone_name': zone_name,
                        'zone_type': zone_type,
                        'duration': dwell_time
                    })

                # Collect actual active person IDs from dwell times and detections
                active_person_ids = set()
                for dwell_entry in analytics_data['dwell_times']:
                    person_id = dwell_entry.get('person_id')
                    if person_id:
                        active_person_ids.add(person_id)

                # Create timestamp-specific data package
                timestamp_data = {
                    'timestamp': datetime.now(UTC).isoformat(),
                    'frame_time': timestamp_str,
                    'detections': len(current_detections),
                    'active_persons': list(active_person_ids),
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

                # === SAVE MERGED LOGS SNAPSHOT (Every 5 seconds) ===
                try:
                    # Get database session for product metrics
                    from app.core.database import SessionLocal
                    db = SessionLocal()

                    try:
                        snapshot_data = collect_analytics_snapshot(
                            current_metrics=current_metrics,
                            zones_data=zones_data,
                            lines_data=lines_data,
                            active_persons=active_persons,
                            current_detections=current_detections,
                            trajectory_tracker=trajectory_tracker,
                            dwell_calculator=dwell_calculator,
                            occupancy_counter=occupancy_counter,
                            line_crossing_detector=line_crossing_detector,
                            queue_detector=queue_detector,
                            heatmap_generator=heatmap_generator,
                            interaction_tracker=interaction_tracker,
                            gaze_detector=gaze_detector,
                            gemini_analysis_text=analysis_text,
                            gemini_structured_data=None,  # Would need structured analysis if available
                            alert_manager=alert_manager,
                            # Product inventory components
                            product_detector=product_detector,
                            product_interaction_tracker=product_interaction_tracker,
                            db_session=db,
                            # Camera info
                            camera_name="Main Store Camera",
                            camera_source=camera.camera_source,
                            room_name="Store Floor 1"
                        )
                    finally:
                        db.close()

                    saved_snapshot = merged_logger.save_camera_snapshot(snapshot_data)
                    if saved_snapshot:
                        log_activity(f"💾 Merged snapshot saved (ID: {saved_snapshot.id})", "system")
                except Exception as e:
                    log_activity(f"❌ Error saving merged snapshot: {str(e)}", "system")
                    print(f"Merged snapshot error: {e}")

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

    # Initialize merged logs database
    try:
        init_merged_db()
        log_activity("✓ Merged logs database initialized", "system")
    except Exception as e:
        log_activity(f"❌ Error initializing merged logs: {str(e)}", "system")

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

    # Initialize product detection after zones are created
    log_activity("🛍️ Initializing product inventory system...", "system")
    threading.Thread(target=initialize_products_in_zones, daemon=True).start()

    # Register frame callback for detection
    camera.register_frame_callback(process_frame)
    log_activity("✓ System ready - Real-time detection active", "system")

    # Start integrated Gemini analysis + alert generation (every 5 seconds)
    threading.Thread(target=continuous_gemini_analysis_and_alerts, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    camera.stop()
    # Release MediaPipe resources
    interaction_detector.release()
    gaze_detector.release()
    log_activity("🛑 System shutdown complete", "system")


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
            tracking_id = str(person_id)  # Use person_id as tracking_id
            trajectory_tracker.update_position(
                tracking_id,
                person_id,
                person_bbox,
                datetime.now(UTC),
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
                    datetime.now(UTC)
                )

            # Check line crossings
            line_crossing_detector.check_crossing(tracking_id, person_id, (center_x, center_y), datetime.now(UTC))

            # === PHASE 2: Hand & Interaction Detection ===
            if zones_data and len(zones_data) > 0:
                interactions = interaction_detector.update(
                    frame=frame,
                    tracking_id=str(person_id),
                    person_id=person_id,
                    person_bbox=person_bbox,
                    zones=zones_data,
                    timestamp=datetime.now(UTC)
                )

                # Update interaction tracker
                for interaction in interactions:
                    if interaction.duration_seconds == 0.0:
                        # New interaction
                        interaction_tracker.start_interaction(
                            tracking_id=str(person_id),
                            person_id=person_id,
                            zone_id=interaction.zone_id,
                            interaction_type=interaction.interaction_type,
                            hand_position=interaction.hand_position,
                            gesture_type=interaction.gesture_type,
                            timestamp=interaction.timestamp
                        )
                    else:
                        # Update existing interaction
                        interaction_tracker.update_interaction(
                            tracking_id=str(person_id),
                            zone_id=interaction.zone_id,
                            interaction_type=interaction.interaction_type,
                            hand_position=interaction.hand_position,
                            gesture_type=interaction.gesture_type,
                            timestamp=datetime.now(UTC)
                        )

            # === PHASE 3: Gaze Detection ===
            gaze_data = gaze_detector.detect_face_and_gaze(
                frame=frame,
                person_bbox=person_bbox
            )

            gaze_target_position = None
            if gaze_data:
                # Update gaze fixation tracking
                fixation = gaze_detector.update_fixation(
                    tracking_id=str(person_id),
                    person_id=person_id,
                    gaze_data=gaze_data,
                    zones=zones_data,
                    timestamp=datetime.now(UTC)
                )

                # Get gaze target position for product tracking
                gaze_target_position = gaze_data.target_position if hasattr(gaze_data, 'target_position') else None

                # Log significant fixations (optional - can be periodic)
                # Uncomment to log every fixation to DB
                # if fixation:
                #     from database import SessionLocal
                #     db = SessionLocal()
                #     try:
                #         gaze_detector.log_gaze_event_to_db(
                #             db=db,
                #             tracking_id=str(person_id),
                #             person_id=person_id,
                #             gaze_data=gaze_data,
                #             fixation=fixation
                #         )
                #     finally:
                #         db.close()

            # === PRODUCT INTERACTION TRACKING ===
            # Track product-specific interactions if person is in a product zone
            if current_zone_id:
                try:
                    from app.core.database import SessionLocal
                    db = SessionLocal()

                    try:
                        # Get hand position and gesture from interactions
                        hand_position = None
                        gesture_type = None

                        if interactions:
                            # Use the latest interaction for hand data
                            latest_interaction = interactions[-1]
                            hand_position = latest_interaction.hand_position
                            gesture_type = latest_interaction.gesture_type

                        # Update product interaction tracker
                        product_interactions = product_interaction_tracker.update(
                            tracking_id=str(person_id),
                            person_id=person_id,
                            zone_id=current_zone_id,
                            hand_position=hand_position,
                            gesture_type=gesture_type,
                            gaze_target_position=gaze_target_position,
                            timestamp=datetime.now(UTC),
                            db=db
                        )

                    finally:
                        db.close()

                except Exception as e:
                    print(f"Error in product interaction tracking: {e}")

        # Cleanup old interactions, fixations, and product interactions
        interaction_detector.cleanup_old_interactions(max_age_seconds=5.0)
        gaze_detector.cleanup_old_fixations(max_age_seconds=5.0)
        interaction_tracker.cleanup_old_interactions(max_age_seconds=10.0)

        # Cleanup old product interactions
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                product_interaction_tracker.cleanup_old_interactions(db, max_age_seconds=10.0)
            finally:
                db.close()
        except Exception as e:
            print(f"Error cleaning up product interactions: {e}")

        # Update occupancy counter with all positions
        zone_occupancies = occupancy_counter.update(person_positions, datetime.now(UTC))

        # Update merged logs users table for detected persons
        try:
            for tracking_id, person_data in active_persons.items():
                person_id = person_data.get('person_id')
                if person_id:
                    # Update last_seen for recognized persons
                    merged_logger.update_user_last_seen(person_id)
        except Exception as e:
            print(f"Error updating merged users: {e}")

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


async def broadcast_inventory_update():
    """Broadcast inventory updates to all connected websockets"""
    from app.core.database import SessionLocal as DB
    disconnected = []

    db = DB()
    try:
        # Get summary data
        from app.api.inventory_routes import get_metrics_summary
        metrics = await get_metrics_summary(db)

        for connection in inventory_connections:
            try:
                await connection.send_json({"type": "inventory", "data": metrics})
            except:
                disconnected.append(connection)

        for conn in disconnected:
            inventory_connections.remove(conn)
    except Exception as e:
        print(f"Error broadcasting inventory: {e}")
    finally:
        db.close()


async def broadcast_customer_update():
    """Broadcast customer updates to all connected websockets"""
    from app.core.database import SessionLocal as DB
    disconnected = []

    db = DB()
    try:
        # Get stats
        stats_data = await get_customer_stats()

        for connection in customer_connections:
            try:
                await connection.send_json({"type": "customers", "data": stats_data})
            except:
                disconnected.append(connection)

        for conn in disconnected:
            customer_connections.remove(conn)
    except Exception as e:
        print(f"Error broadcasting customers: {e}")
    finally:
        db.close()




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


@app.websocket("/ws/inventory")
async def websocket_inventory(websocket: WebSocket):
    """WebSocket endpoint for real-time inventory updates"""
    await websocket.accept()
    inventory_connections.append(websocket)

    try:
        # Send initial inventory data on connect
        from app.core.database import SessionLocal as DB
        db = DB()
        try:
            from app.api.inventory_routes import get_metrics_summary
            metrics = await get_metrics_summary(db)
            await websocket.send_json({"type": "inventory", "data": metrics})
        finally:
            db.close()

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in inventory_connections:
            inventory_connections.remove(websocket)


@app.websocket("/ws/customers")
async def websocket_customers(websocket: WebSocket):
    """WebSocket endpoint for real-time customer updates"""
    await websocket.accept()
    customer_connections.append(websocket)

    try:
        # Send initial customer stats on connect
        stats = await get_customer_stats()
        await websocket.send_json({"type": "customers", "data": stats})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in customer_connections:
            customer_connections.remove(websocket)


@app.get("/video_feed")
async def video_feed():
    """Stream live video feed with overlays"""
    def generate():
        while True:
            frame = camera.get_current_frame()
            if frame is not None:
                # Get analytics data (create copies to avoid concurrent modification)
                trajectories = dict(trajectory_tracker.active_trajectories)
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


# ==================== MANUAL OBSERVATION & TIMELINE APIs ====================

# Pydantic models for request bodies
class ManualObservationCreate(BaseModel):
    observation_type: str  # note, issue, feedback, action_taken
    title: Optional[str] = None
    description: str
    severity: str = "info"  # info, warning, critical
    recorded_by: Optional[str] = "staff"
    requires_followup: bool = False


from app.core.database import (
    SessionLocal, ManualObservation, Person, BodyDetectionEvent,
    PersonSession, BehaviorAnalysis, SceneAnalysis, EventLog
)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/observations/person/{person_id}")
async def create_person_observation(person_id: int, observation: ManualObservationCreate):
    """Add a manual observation for a specific person"""
    db = SessionLocal()
    try:
        # Check if person exists
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail=f"Person {person_id} not found")

        # Create observation
        db_observation = ManualObservation(
            person_id=person_id,
            observation_type=observation.observation_type,
            title=observation.title,
            description=observation.description,
            severity=observation.severity,
            recorded_by=observation.recorded_by,
            requires_followup=observation.requires_followup,
            timestamp=datetime.utcnow()
        )

        db.add(db_observation)
        db.commit()
        db.refresh(db_observation)

        log_activity(f"📝 Manual observation added for Person #{person_id}: {observation.title or observation.description[:50]}", "system")

        return {
            "success": True,
            "observation_id": db_observation.id,
            "message": f"Observation added for Person #{person_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/api/observations/tracking/{tracking_id}")
async def create_tracking_observation(tracking_id: str, observation: ManualObservationCreate):
    """Add a manual observation for a specific body tracking ID"""
    db = SessionLocal()
    try:
        # Check if tracking ID exists
        session = db.query(PersonSession).filter(
            PersonSession.body_tracking_id == tracking_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail=f"Tracking ID {tracking_id} not found")

        # Create observation
        db_observation = ManualObservation(
            body_tracking_id=tracking_id,
            person_id=session.person_id,  # Link to person if known
            observation_type=observation.observation_type,
            title=observation.title,
            description=observation.description,
            severity=observation.severity,
            recorded_by=observation.recorded_by,
            requires_followup=observation.requires_followup,
            timestamp=datetime.utcnow()
        )

        db.add(db_observation)
        db.commit()
        db.refresh(db_observation)

        log_activity(f"📝 Manual observation added for tracking {tracking_id}: {observation.title or observation.description[:50]}", "system")

        return {
            "success": True,
            "observation_id": db_observation.id,
            "message": f"Observation added for tracking ID {tracking_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/person/{person_id}/timeline")
async def get_person_timeline(person_id: int):
    """Get complete timeline for a person: detections, body tracking, analyses, observations"""
    db = SessionLocal()
    try:
        # Check if person exists
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail=f"Person {person_id} not found")

        # Get all body detection events for this person
        body_detections = db.query(BodyDetectionEvent).filter(
            BodyDetectionEvent.person_id == person_id
        ).order_by(BodyDetectionEvent.timestamp.desc()).limit(100).all()

        # Get all person sessions
        sessions = db.query(PersonSession).filter(
            PersonSession.person_id == person_id
        ).order_by(PersonSession.session_start.desc()).all()

        # Get all behavior analyses
        analyses = db.query(BehaviorAnalysis).filter(
            BehaviorAnalysis.person_id == person_id
        ).order_by(BehaviorAnalysis.timestamp.desc()).all()

        # Get all manual observations
        observations = db.query(ManualObservation).filter(
            ManualObservation.person_id == person_id
        ).order_by(ManualObservation.timestamp.desc()).all()

        # Build timeline response
        timeline = {
            "person": {
                "id": person.id,
                "name": person.name,
                "first_seen": person.first_seen.isoformat() if person.first_seen else None,
                "last_seen": person.last_seen.isoformat() if person.last_seen else None,
                "visit_count": person.visit_count,
                "thumbnail_path": person.thumbnail_path
            },
            "sessions": [
                {
                    "id": s.id,
                    "tracking_id": s.body_tracking_id,
                    "start": s.session_start.isoformat() if s.session_start else None,
                    "end": s.session_end.isoformat() if s.session_end else None,
                    "is_active": s.is_active,
                    "zones_visited": s.zones_visited,
                    "total_detections": s.total_detections
                }
                for s in sessions
            ],
            "recent_detections": [
                {
                    "id": d.id,
                    "tracking_id": d.body_tracking_id,
                    "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                    "confidence": d.confidence,
                    "zone_id": d.zone_id
                }
                for d in body_detections
            ],
            "analyses": [
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "type": a.analysis_type,
                    "tracking_id": a.body_tracking_id,
                    "text": a.analysis_text,
                    "structured_data": a.structured_data
                }
                for a in analyses
            ],
            "observations": [
                {
                    "id": o.id,
                    "timestamp": o.timestamp.isoformat() if o.timestamp else None,
                    "type": o.observation_type,
                    "title": o.title,
                    "description": o.description,
                    "severity": o.severity,
                    "recorded_by": o.recorded_by,
                    "tracking_id": o.body_tracking_id
                }
                for o in observations
            ]
        }

        return timeline

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/tracking/{tracking_id}/timeline")
async def get_tracking_timeline(tracking_id: str):
    """Get timeline for a specific body tracking ID (for unknown persons)"""
    db = SessionLocal()
    try:
        # Get session for this tracking ID
        session = db.query(PersonSession).filter(
            PersonSession.body_tracking_id == tracking_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail=f"Tracking ID {tracking_id} not found")

        # Get all body detection events
        body_detections = db.query(BodyDetectionEvent).filter(
            BodyDetectionEvent.body_tracking_id == tracking_id
        ).order_by(BodyDetectionEvent.timestamp.desc()).all()

        # Get all behavior analyses
        analyses = db.query(BehaviorAnalysis).filter(
            BehaviorAnalysis.body_tracking_id == tracking_id
        ).order_by(BehaviorAnalysis.timestamp.desc()).all()

        # Get all manual observations
        observations = db.query(ManualObservation).filter(
            ManualObservation.body_tracking_id == tracking_id
        ).order_by(ManualObservation.timestamp.desc()).all()

        # Build timeline response
        timeline = {
            "tracking_id": tracking_id,
            "person_id": session.person_id,
            "session": {
                "id": session.id,
                "start": session.session_start.isoformat() if session.session_start else None,
                "end": session.session_end.isoformat() if session.session_end else None,
                "is_active": session.is_active,
                "zones_visited": session.zones_visited,
                "total_detections": session.total_detections
            },
            "detections": [
                {
                    "id": d.id,
                    "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                    "confidence": d.confidence,
                    "zone_id": d.zone_id,
                    "bbox": {
                        "left": d.bbox_left,
                        "top": d.bbox_top,
                        "right": d.bbox_right,
                        "bottom": d.bbox_bottom
                    }
                }
                for d in body_detections
            ],
            "analyses": [
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "type": a.analysis_type,
                    "text": a.analysis_text,
                    "structured_data": a.structured_data
                }
                for a in analyses
            ],
            "observations": [
                {
                    "id": o.id,
                    "timestamp": o.timestamp.isoformat() if o.timestamp else None,
                    "type": o.observation_type,
                    "title": o.title,
                    "description": o.description,
                    "severity": o.severity,
                    "recorded_by": o.recorded_by
                }
                for o in observations
            ]
        }

        return timeline

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/scene/timeline")
async def get_scene_timeline(start: Optional[str] = None, end: Optional[str] = None, limit: int = 50):
    """Get scene analyses and events within a time range"""
    db = SessionLocal()
    try:
        query = db.query(SceneAnalysis)

        # Apply time filters if provided
        if start:
            try:
                start_dt = datetime.fromisoformat(start)
                query = query.filter(SceneAnalysis.timestamp >= start_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start datetime format")

        if end:
            try:
                end_dt = datetime.fromisoformat(end)
                query = query.filter(SceneAnalysis.timestamp <= end_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end datetime format")

        # Order by timestamp descending and limit
        scene_analyses = query.order_by(SceneAnalysis.timestamp.desc()).limit(limit).all()

        # Build response
        timeline = []
        for scene in scene_analyses:
            # Get associated events
            events = db.query(EventLog).filter(
                EventLog.scene_analysis_id == scene.id
            ).all()

            timeline.append({
                "scene_id": scene.id,
                "timestamp": scene.timestamp.isoformat() if scene.timestamp else None,
                "time_window": {
                    "start": scene.time_window_start,
                    "end": scene.time_window_end
                },
                "scene": {
                    "summary": scene.overall_summary,
                    "crowd_density": scene.crowd_density,
                    "energy_level": scene.energy_level,
                    "dominant_activities": scene.dominant_activities
                },
                "events": [
                    {
                        "id": e.id,
                        "timestamp": e.video_timestamp,
                        "type": e.event_type,
                        "severity": e.severity,
                        "description": e.description,
                        "location": e.location,
                        "involved_tracking_ids": e.involved_tracking_ids,
                        "requires_action": e.requires_action
                    }
                    for e in events
                ],
                "video_clip_path": scene.video_clip_path
            })

        return {
            "count": len(timeline),
            "timeline": timeline
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ==================== STAFF MANAGEMENT ENDPOINTS ====================

@app.post("/api/staff/clock-in")
async def staff_clock_in(employee_id: str):
    """Staff member clocks in for shift"""
    db = SessionLocal()
    try:
        from app.core.database import StaffMember
        staff = db.query(StaffMember).filter(
            StaffMember.employee_id == employee_id
        ).first()

        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        staff.is_on_duty = True
        staff.shift_start = datetime.now(UTC)
        db.commit()

        log_activity(f"👤 {staff.name} clocked in", "system")

        return {"success": True, "staff": staff.name, "shift_start": staff.shift_start.isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/api/staff/clock-out")
async def staff_clock_out(employee_id: str):
    """Staff member clocks out from shift"""
    db = SessionLocal()
    try:
        from app.core.database import StaffMember
        staff = db.query(StaffMember).filter(
            StaffMember.employee_id == employee_id
        ).first()

        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")

        staff.is_on_duty = False
        staff.shift_end = datetime.now(UTC)
        db.commit()

        log_activity(f"👤 {staff.name} clocked out", "system")

        return {"success": True, "staff": staff.name}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/staff/assignments/{staff_id}")
async def get_staff_assignments(staff_id: int):
    """Get active assignments for staff member"""
    db = SessionLocal()
    try:
        from app.core.database import AlertAssignment
        assignments = db.query(AlertAssignment).filter(
            AlertAssignment.staff_id == staff_id,
            AlertAssignment.completed_at == None
        ).all()

        return [
            {
                "alert_id": a.alert_id,
                "assigned_at": a.assigned_at.isoformat(),
                "time_elapsed": (datetime.now(UTC) - a.assigned_at).seconds
            }
            for a in assignments
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/api/staff/assignment/{alert_id}/complete")
async def complete_assignment(alert_id: str, outcome: str = "success", notes: str = None):
    """Mark alert assignment as complete"""
    db = SessionLocal()
    try:
        from Agent.staff_coordinator import StaffCoordinator
        staff_coordinator = StaffCoordinator(api_key=os.getenv("GEMINI_API_KEY"))

        staff_coordinator.track_assignment_outcome(
            db, alert_id, outcome, staff_notes=notes
        )

        return {"success": True, "outcome": outcome}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/staff/list")
async def list_staff():
    """Get list of all staff members"""
    db = SessionLocal()
    try:
        from database import StaffMember
        staff = db.query(StaffMember).all()

        return [
            {
                "id": s.id,
                "employee_id": s.employee_id,
                "name": s.name,
                "role": s.role,
                "is_on_duty": s.is_on_duty,
                "shift_start": s.shift_start.isoformat() if s.shift_start else None,
                "shift_end": s.shift_end.isoformat() if s.shift_end else None
            }
            for s in staff
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ==================== CUSTOMER RECOGNITION ENDPOINTS ====================

@app.get("/api/customers/profile/{profile_uuid}")
async def get_customer_profile(profile_uuid: str):
    """Get customer profile insights (privacy-compliant)"""
    db = SessionLocal()
    try:
        from app.core.database import CustomerProfile
        from customer_recognition import CustomerRecognitionAgent

        profile = db.query(CustomerProfile).filter(
            CustomerProfile.profile_uuid == profile_uuid
        ).first()

        if not profile or profile.opt_out_date:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Initialize recognition agent
        customer_recognition = CustomerRecognitionAgent(enabled=True)

        insights = customer_recognition.get_customer_insights(db, profile.id)

        return insights

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/api/customers/opt-out/{profile_uuid}")
async def customer_opt_out(profile_uuid: str):
    """Handle customer opt-out request (GDPR compliance)"""
    db = SessionLocal()
    try:
        from app.core.database import CustomerProfile
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.profile_uuid == profile_uuid
        ).first()

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Mark for deletion
        profile.opt_out_date = datetime.now(UTC)
        profile.appearance_embedding = None  # Clear embedding
        profile.data_retention_expires = datetime.now(UTC) + timedelta(days=30)

        db.commit()

        log_activity(f"🔒 Customer profile {profile_uuid} opted out (GDPR)", "system")

        return {"success": True, "message": "Profile will be deleted in 30 days"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/customers/stats")
async def get_customer_stats():
    """Get customer recognition statistics"""
    db = SessionLocal()
    try:
        from app.core.database import CustomerProfile, CustomerVisit
        total_profiles = db.query(CustomerProfile).filter(
            CustomerProfile.opt_out_date == None
        ).count()

        vip_count = db.query(CustomerProfile).filter(
            CustomerProfile.vip_status == True,
            CustomerProfile.opt_out_date == None
        ).count()

        total_visits = db.query(CustomerVisit).count()

        # Recent visitors (last 7 days)
        recent_cutoff = datetime.now(UTC) - timedelta(days=7)
        recent_visitors = db.query(CustomerProfile).filter(
            CustomerProfile.last_visit >= recent_cutoff,
            CustomerProfile.opt_out_date == None
        ).count()

        # Active visitors (last 1 hour)
        active_cutoff = datetime.now(UTC) - timedelta(hours=1)
        active_visitors = db.query(CustomerProfile).filter(
            CustomerProfile.last_visit >= active_cutoff,
            CustomerProfile.opt_out_date == None
        ).count()

        return {
            "total_profiles": total_profiles,
            "vip_customers": vip_count,
            "total_visits": total_visits,
            "recent_visitors_7d": recent_visitors,
            "active_visitors": active_visitors
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/customers/list")
async def get_customer_list(limit: int = 20, active_only: bool = False):
    """Get list of customers with basic info"""
    db = SessionLocal()
    try:
        from app.core.database import CustomerProfile

        query = db.query(CustomerProfile).filter(
            CustomerProfile.opt_out_date == None
        )

        if active_only:
            # Active in last hour
            active_cutoff = datetime.now(UTC) - timedelta(hours=1)
            query = query.filter(CustomerProfile.last_visit >= active_cutoff)

        customers = query.order_by(CustomerProfile.last_visit.desc()).limit(limit).all()

        return [
            {
                "id": c.id,
                "profile_uuid": c.profile_uuid,
                "first_visit": c.first_visit.isoformat() if c.first_visit else None,
                "last_visit": c.last_visit.isoformat() if c.last_visit else None,
                "total_visits": c.total_visits,
                "visit_frequency": c.visit_frequency,
                "favorite_zones": c.favorite_zones,
                "avg_visit_duration": c.avg_visit_duration_minutes,
                "vip_status": c.vip_status,
                "purchase_intent_score": c.avg_purchase_intent_score,
                "preferred_categories": c.preferred_product_categories
            }
            for c in customers
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/customers/recent-visits")
async def get_recent_customer_visits(hours: int = 24, limit: int = 50):
    """Get recent customer visits"""
    db = SessionLocal()
    try:
        from app.core.database import CustomerVisit, CustomerProfile

        cutoff = datetime.now(UTC) - timedelta(hours=hours)

        visits = db.query(CustomerVisit).filter(
            CustomerVisit.visit_date >= cutoff
        ).order_by(CustomerVisit.visit_date.desc()).limit(limit).all()

        result = []
        for visit in visits:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.id == visit.profile_id
            ).first()

            if profile and not profile.opt_out_date:
                result.append({
                    "visit_id": visit.id,
                    "profile_uuid": profile.profile_uuid,
                    "vip_status": profile.vip_status,
                    "visit_date": visit.visit_date.isoformat(),
                    "duration_minutes": visit.duration_minutes,
                    "zones_visited": visit.zones_visited,
                    "purchase_intent_score": visit.purchase_intent_score,
                    "staff_interactions": visit.staff_interactions_count,
                    "satisfaction_score": visit.satisfaction_score
                })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


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
