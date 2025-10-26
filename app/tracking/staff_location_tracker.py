"""
Staff Location Tracking
Receives location updates from mobile apps or Bluetooth beacons
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
from datetime import datetime, UTC
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, StaffLocation, StaffMember

router = APIRouter()

# Active staff connections
staff_connections: Dict[int, WebSocket] = {}


@router.websocket("/ws/staff/{employee_id}")
async def staff_location_websocket(websocket: WebSocket, employee_id: str):
    """
    WebSocket for staff location updates

    Usage:
    - Staff mobile app connects with employee_id
    - Sends periodic location updates
    - Receives alert assignments in real-time

    Message format (from app):
    {
        "x": 0.5,  # Normalized x position (0-1)
        "y": 0.7,  # Normalized y position (0-1)
        "zone_id": 3,  # Optional zone ID
        "is_available": true,  # Availability status
        "current_task": "Assisting customer"  # Optional task description
    }
    """
    await websocket.accept()

    db = SessionLocal()

    # Get staff member
    staff = db.query(StaffMember).filter(
        StaffMember.employee_id == employee_id
    ).first()

    if not staff:
        await websocket.close(code=1008, reason="Invalid employee ID")
        db.close()
        return

    staff_connections[staff.id] = websocket
    print(f"[Staff Tracker] {staff.name} (ID: {staff.id}) connected")

    # Send welcome message
    await websocket.send_json({
        "type": "welcome",
        "message": f"Welcome, {staff.name}!",
        "staff_id": staff.id
    })

    try:
        while True:
            # Receive location update
            data = await websocket.receive_json()

            # Validate data
            if 'x' not in data or 'y' not in data:
                await websocket.send_json({
                    "type": "error",
                    "message": "Missing x or y coordinates"
                })
                continue

            # Save location
            location = StaffLocation(
                staff_id=staff.id,
                x_position=float(data['x']),
                y_position=float(data['y']),
                zone_id=data.get('zone_id'),
                is_available=data.get('is_available', True),
                current_task=data.get('current_task'),
                timestamp=datetime.now(UTC)
            )

            db.add(location)
            db.commit()

            # Acknowledge
            await websocket.send_json({
                "type": "location_updated",
                "status": "success",
                "timestamp": location.timestamp.isoformat()
            })

    except WebSocketDisconnect:
        if staff.id in staff_connections:
            del staff_connections[staff.id]
        print(f"[Staff Tracker] {staff.name} disconnected")
        db.close()
    except Exception as e:
        print(f"[Staff Tracker] Error for {staff.name}: {e}")
        if staff.id in staff_connections:
            del staff_connections[staff.id]
        db.close()


async def send_alert_to_staff(staff_id: int, alert_data: dict):
    """
    Send alert assignment to staff member

    Args:
        staff_id: Staff member ID
        alert_data: Alert information to send
    """
    if staff_id in staff_connections:
        ws = staff_connections[staff_id]
        try:
            await ws.send_json({
                "type": "alert_assignment",
                "data": alert_data
            })
            print(f"[Staff Tracker] Sent alert to staff {staff_id}")
        except Exception as e:
            print(f"[Staff Tracker] Failed to send alert to staff {staff_id}: {e}")
            # Connection lost
            if staff_id in staff_connections:
                del staff_connections[staff_id]
    else:
        print(f"[Staff Tracker] Staff {staff_id} not connected")


async def broadcast_to_all_staff(message: dict):
    """
    Broadcast message to all connected staff

    Args:
        message: Message dictionary to broadcast
    """
    disconnected = []

    for staff_id, ws in staff_connections.items():
        try:
            await ws.send_json(message)
        except:
            disconnected.append(staff_id)

    # Clean up disconnected
    for staff_id in disconnected:
        del staff_connections[staff_id]


def get_connected_staff_count() -> int:
    """Get count of currently connected staff"""
    return len(staff_connections)


def get_connected_staff_ids() -> List[int]:
    """Get list of currently connected staff IDs"""
    return list(staff_connections.keys())
