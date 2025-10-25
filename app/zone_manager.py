"""
Zone Management System
API for creating, editing, and managing store zones and virtual lines
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import get_db, Zone, VirtualLine


router = APIRouter(prefix="/api/zones", tags=["zones"])


# ==================== PYDANTIC MODELS ====================

class ZoneCreate(BaseModel):
    name: str
    zone_type: str  # "product", "queue", "entrance", "aisle"
    polygon_points: List[List[float]]  # [[x1,y1], [x2,y2], ...]
    color: Optional[str] = "#00FF00"
    max_capacity: Optional[int] = None


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    zone_type: Optional[str] = None
    polygon_points: Optional[List[List[float]]] = None
    color: Optional[str] = None
    max_capacity: Optional[int] = None
    is_active: Optional[bool] = None


class ZoneResponse(BaseModel):
    id: int
    name: str
    zone_type: str
    polygon_points: List[List[float]]
    color: str
    is_active: bool
    max_capacity: Optional[int]

    class Config:
        from_attributes = True


class VirtualLineCreate(BaseModel):
    name: str
    start_point: dict  # {"x": 0.2, "y": 0.5}
    end_point: dict    # {"x": 0.8, "y": 0.5}
    count_direction: Optional[str] = "both"  # "both", "in", "out"
    color: Optional[str] = "#FF0000"


class VirtualLineUpdate(BaseModel):
    name: Optional[str] = None
    start_point: Optional[dict] = None
    end_point: Optional[dict] = None
    count_direction: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class VirtualLineResponse(BaseModel):
    id: int
    name: str
    start_point: dict
    end_point: dict
    count_direction: str
    color: str
    is_active: bool

    class Config:
        from_attributes = True


# ==================== ZONE ENDPOINTS ====================

@router.post("/", response_model=ZoneResponse)
def create_zone(zone: ZoneCreate, db: Session = Depends(get_db)):
    """Create a new zone"""
    db_zone = Zone(
        name=zone.name,
        zone_type=zone.zone_type,
        polygon_points=zone.polygon_points,
        color=zone.color,
        max_capacity=zone.max_capacity
    )
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone


@router.get("/", response_model=List[ZoneResponse])
def get_all_zones(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all zones"""
    query = db.query(Zone)
    if active_only:
        query = query.filter(Zone.is_active == True)
    return query.all()


@router.get("/{zone_id}", response_model=ZoneResponse)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    """Get specific zone by ID"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.put("/{zone_id}", response_model=ZoneResponse)
def update_zone(zone_id: int, zone_update: ZoneUpdate, db: Session = Depends(get_db)):
    """Update a zone"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    for field, value in zone_update.dict(exclude_unset=True).items():
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}")
def delete_zone(zone_id: int, db: Session = Depends(get_db)):
    """Delete a zone (soft delete by setting is_active=False)"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    zone.is_active = False
    db.commit()
    return {"message": "Zone deactivated successfully"}


# ==================== VIRTUAL LINE ENDPOINTS ====================

@router.post("/lines", response_model=VirtualLineResponse)
def create_virtual_line(line: VirtualLineCreate, db: Session = Depends(get_db)):
    """Create a new virtual line"""
    db_line = VirtualLine(
        name=line.name,
        start_point=line.start_point,
        end_point=line.end_point,
        count_direction=line.count_direction,
        color=line.color
    )
    db.add(db_line)
    db.commit()
    db.refresh(db_line)
    return db_line


@router.get("/lines", response_model=List[VirtualLineResponse])
def get_all_virtual_lines(active_only: bool = True, db: Session = Depends(get_db)):
    """Get all virtual lines"""
    query = db.query(VirtualLine)
    if active_only:
        query = query.filter(VirtualLine.is_active == True)
    return query.all()


@router.get("/lines/{line_id}", response_model=VirtualLineResponse)
def get_virtual_line(line_id: int, db: Session = Depends(get_db)):
    """Get specific virtual line by ID"""
    line = db.query(VirtualLine).filter(VirtualLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Virtual line not found")
    return line


@router.put("/lines/{line_id}", response_model=VirtualLineResponse)
def update_virtual_line(
    line_id: int,
    line_update: VirtualLineUpdate,
    db: Session = Depends(get_db)
):
    """Update a virtual line"""
    line = db.query(VirtualLine).filter(VirtualLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Virtual line not found")

    for field, value in line_update.dict(exclude_unset=True).items():
        setattr(line, field, value)

    db.commit()
    db.refresh(line)
    return line


@router.delete("/lines/{line_id}")
def delete_virtual_line(line_id: int, db: Session = Depends(get_db)):
    """Delete a virtual line"""
    line = db.query(VirtualLine).filter(VirtualLine.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Virtual line not found")

    line.is_active = False
    db.commit()
    return {"message": "Virtual line deactivated successfully"}


# ==================== PRESET ZONES ====================

def create_default_zones(db: Session):
    """Create default zones for a retail store"""
    default_zones = [
        {
            "name": "Entrance",
            "zone_type": "entrance",
            "polygon_points": [[0.0, 0.0], [0.3, 0.0], [0.3, 0.2], [0.0, 0.2]],
            "color": "#00FF00",
            "max_capacity": 10
        },
        {
            "name": "Checkout",
            "zone_type": "queue",
            "polygon_points": [[0.7, 0.8], [1.0, 0.8], [1.0, 1.0], [0.7, 1.0]],
            "color": "#FFA500",
            "max_capacity": 20
        },
        {
            "name": "Electronics",
            "zone_type": "product",
            "polygon_points": [[0.0, 0.3], [0.4, 0.3], [0.4, 0.6], [0.0, 0.6]],
            "color": "#0000FF",
            "max_capacity": 30
        },
        {
            "name": "Clothing",
            "zone_type": "product",
            "polygon_points": [[0.6, 0.0], [1.0, 0.0], [1.0, 0.5], [0.6, 0.5]],
            "color": "#FF00FF",
            "max_capacity": 40
        }
    ]

    for zone_data in default_zones:
        # Check if zone already exists
        existing = db.query(Zone).filter(Zone.name == zone_data["name"]).first()
        if not existing:
            zone = Zone(**zone_data)
            db.add(zone)

    db.commit()
    print("Default zones created")


def create_default_lines(db: Session):
    """Create default virtual lines"""
    default_lines = [
        {
            "name": "Store Entrance",
            "start_point": {"x": 0.0, "y": 0.2},
            "end_point": {"x": 0.3, "y": 0.2},
            "count_direction": "both",
            "color": "#FF0000"
        },
        {
            "name": "Checkout Line 1",
            "start_point": {"x": 0.7, "y": 0.8},
            "end_point": {"x": 0.85, "y": 0.8},
            "count_direction": "in",
            "color": "#FFFF00"
        }
    ]

    for line_data in default_lines:
        # Check if line already exists
        existing = db.query(VirtualLine).filter(VirtualLine.name == line_data["name"]).first()
        if not existing:
            line = VirtualLine(**line_data)
            db.add(line)

    db.commit()
    print("Default virtual lines created")
