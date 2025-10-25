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
from gemini_analyzer import GeminiAnalyzer
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Video AI Surveillance System")

# Initialize components
camera = CameraManager(camera_source=int(os.getenv("CAMERA_SOURCE", 0)))
face_detector = FaceDetector(tolerance=0.6)
gemini_analyzer = GeminiAnalyzer(api_key=os.getenv("GEMINI_API_KEY"))

# WebSocket connections
active_connections: List[WebSocket] = []

# Global state
current_detected_person = None
analysis_in_progress = False


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    init_db()
    print("Database initialized")

    # Create directories
    os.makedirs("uploads/frames", exist_ok=True)
    os.makedirs("uploads/thumbnails", exist_ok=True)
    os.makedirs("temp_videos", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    # Start camera
    camera.start()

    # Load known faces
    db = next(get_db())
    face_detector.load_known_faces_from_db(db)

    # Register frame callback for detection
    camera.register_frame_callback(process_frame)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    camera.stop()


def process_frame(frame):
    """Process each camera frame for face detection"""
    global current_detected_person, analysis_in_progress

    # Detect faces
    detected_faces = face_detector.detect_faces(frame)

    if len(detected_faces) > 0:
        for face_encoding, face_location in detected_faces:
            # Try to recognize face
            person_id = face_detector.recognize_face(face_encoding)

            db = next(get_db())

            if person_id:
                # Known person detected
                person = db.query(Person).filter(Person.id == person_id).first()
                face_detector.update_person_visit(db, person_id)

                # Log detection event
                frame_path = camera.save_frame(frame)
                event = face_detector.log_detection_event(
                    db, person_id, 0.95, frame_path
                )

                # Send to dashboard
                current_detected_person = {
                    "id": person.id,
                    "name": person.name,
                    "visit_count": person.visit_count,
                    "first_seen": person.first_seen.isoformat(),
                    "last_seen": person.last_seen.isoformat(),
                    "thumbnail": person.thumbnail_path,
                    "is_new": False
                }

                # Trigger behavior analysis in background
                if not analysis_in_progress:
                    threading.Thread(
                        target=trigger_behavior_analysis,
                        args=(person_id, event.id),
                        daemon=True
                    ).start()

            else:
                # Unknown person - add to database
                person = face_detector.add_person_to_db(
                    db, face_encoding, frame, face_location
                )

                # Log detection event
                frame_path = camera.save_frame(frame)
                event = face_detector.log_detection_event(
                    db, person.id, 0.90, frame_path
                )

                current_detected_person = {
                    "id": person.id,
                    "name": person.name,
                    "visit_count": 1,
                    "first_seen": person.first_seen.isoformat(),
                    "last_seen": person.last_seen.isoformat(),
                    "thumbnail": person.thumbnail_path,
                    "is_new": True
                }

                # Trigger behavior analysis
                if not analysis_in_progress:
                    threading.Thread(
                        target=trigger_behavior_analysis,
                        args=(person.id, event.id),
                        daemon=True
                    ).start()

            # Broadcast to all connected clients
            asyncio.run(broadcast_detection(current_detected_person))


def trigger_behavior_analysis(person_id: int, event_id: int):
    """Trigger Gemini analysis for detected person"""
    global analysis_in_progress

    try:
        analysis_in_progress = True

        # Record 10-second clip
        print("Recording clip for analysis...")
        video_path = camera.record_clip(duration=10)

        # Analyze with Gemini
        print("Analyzing behavior with Gemini...")
        analysis_result = gemini_analyzer.analyze_behavior(video_path)

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


@app.get("/video_feed")
async def video_feed():
    """Stream live video feed"""
    def generate():
        while True:
            frame = camera.get_current_frame()
            if frame is not None:
                # Encode frame
                jpg_bytes = camera.encode_frame_to_jpg(frame)
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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard HTML"""
    with open("static/index.html", "r") as f:
        return f.read()


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
