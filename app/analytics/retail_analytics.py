"""
Retail Analytics Computer Vision Modules
Handles trajectory tracking, dwell time, occupancy, heatmaps, line crossing, and queue detection
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta, UTC
from collections import defaultdict
from scipy.ndimage import gaussian_filter
from sqlalchemy.orm import Session
import uuid
import json

from app.core.database import (
    PersonTrajectory, DwellTimeRecord, Zone, VirtualLine,
    LineCrossingEvent, OccupancyLog, QueueMetrics, HeatmapData, ProductInteraction, GazeEvent
)


class TrajectoryTracker:
    """Track person movement paths using tracking_id"""

    def __init__(self, history_duration_seconds: int = 30):
        self.active_trajectories: Dict[str, List[Dict]] = {}  # {tracking_id: [points]}
        self.session_ids: Dict[str, str] = {}  # {tracking_id: session_uuid}
        self.tracking_to_person: Dict[str, Optional[int]] = {}  # {tracking_id: person_id}
        self.history_duration = history_duration_seconds

    def update_position(
        self,
        tracking_id: str,
        person_id: Optional[int],
        bbox: Tuple[int, int, int, int],
        timestamp: datetime,
        frame_width: int,
        frame_height: int,
        current_zone_id: Optional[int] = None
    ):
        """Update tracked body's position in trajectory"""
        # Calculate centroid from bounding box
        left, top, right, bottom = bbox
        centroid_x = (left + right) / 2
        centroid_y = (top + bottom) / 2

        # Normalize coordinates (0-1)
        norm_x = centroid_x / frame_width
        norm_y = centroid_y / frame_height

        # Create or get session ID
        if tracking_id not in self.session_ids:
            self.session_ids[tracking_id] = str(uuid.uuid4())

        # Update person_id mapping
        if person_id is not None:
            self.tracking_to_person[tracking_id] = person_id

        # Add to trajectory
        if tracking_id not in self.active_trajectories:
            self.active_trajectories[tracking_id] = []

        point = {
            'x': norm_x,
            'y': norm_y,
            'timestamp': timestamp,
            'zone_id': current_zone_id,
            'person_id': person_id
        }
        self.active_trajectories[tracking_id].append(point)

        # Clean old points
        self._clean_old_points(tracking_id, timestamp)

        return norm_x, norm_y

    def _clean_old_points(self, tracking_id: str, current_time: datetime):
        """Remove trajectory points older than history duration"""
        if tracking_id not in self.active_trajectories:
            return

        cutoff_time = current_time - timedelta(seconds=self.history_duration)
        self.active_trajectories[tracking_id] = [
            point for point in self.active_trajectories[tracking_id]
            if point['timestamp'] > cutoff_time
        ]

    def get_path(self, tracking_id: str) -> List[Dict]:
        """Get trajectory path for a tracking ID"""
        return self.active_trajectories.get(tracking_id, [])

    def save_to_db(self, db: Session, tracking_id: str):
        """Save trajectory to database"""
        if tracking_id not in self.active_trajectories:
            return

        session_id = self.session_ids.get(tracking_id)
        person_id = self.tracking_to_person.get(tracking_id)

        for point in self.active_trajectories[tracking_id]:
            trajectory = PersonTrajectory(
                person_id=person_id or point.get('person_id'),
                body_tracking_id=tracking_id,
                session_id=session_id,
                timestamp=point['timestamp'],
                x_position=point['x'],
                y_position=point['y'],
                zone_id=point.get('zone_id')
            )
            db.add(trajectory)

        db.commit()

    def end_session(self, tracking_id: str):
        """End tracking session for tracking_id"""
        if tracking_id in self.active_trajectories:
            del self.active_trajectories[tracking_id]
        if tracking_id in self.session_ids:
            del self.session_ids[tracking_id]
        if tracking_id in self.tracking_to_person:
            del self.tracking_to_person[tracking_id]


class DwellTimeCalculator:
    """Calculate time spent in zones using tracking_id"""

    def __init__(self, stationary_threshold_meters: float = 0.5):
        self.zone_entries: Dict[Tuple[str, int], Dict] = {}  # {(tracking_id, zone_id): data}
        self.stationary_threshold = stationary_threshold_meters
        self.session_ids: Dict[str, str] = {}  # {tracking_id: session_uuid}
        self.tracking_to_person: Dict[str, Optional[int]] = {}  # {tracking_id: person_id}

    def update(
        self,
        tracking_id: str,
        person_id: Optional[int],
        current_zone_id: Optional[int],
        position: Tuple[float, float],
        timestamp: datetime
    ) -> Optional[float]:
        """Update dwell time calculation"""
        if current_zone_id is None:
            return None

        # Get or create session ID
        if tracking_id not in self.session_ids:
            self.session_ids[tracking_id] = str(uuid.uuid4())

        # Update person_id mapping
        if person_id is not None:
            self.tracking_to_person[tracking_id] = person_id

        key = (tracking_id, current_zone_id)

        # Check if entered new zone
        if key not in self.zone_entries:
            self.zone_entries[key] = {
                'entry_time': timestamp,
                'last_position': position,
                'session_id': self.session_ids[tracking_id],
                'person_id': person_id
            }
            return 0

        # Calculate dwell duration
        entry_data = self.zone_entries[key]
        dwell_duration = (timestamp - entry_data['entry_time']).total_seconds()

        # Update last position and person_id
        entry_data['last_position'] = position
        if person_id is not None:
            entry_data['person_id'] = person_id

        return dwell_duration

    def exit_zone(
        self,
        db: Session,
        tracking_id: str,
        zone_id: int,
        exit_time: datetime,
        engagement_score: Optional[float] = None
    ):
        """Record zone exit and save to database"""
        key = (tracking_id, zone_id)
        if key not in self.zone_entries:
            return

        entry_data = self.zone_entries[key]
        duration = (exit_time - entry_data['entry_time']).total_seconds()

        person_id = entry_data.get('person_id') or self.tracking_to_person.get(tracking_id)

        # Save to database
        dwell_record = DwellTimeRecord(
            person_id=person_id,
            body_tracking_id=tracking_id,
            session_id=entry_data['session_id'],
            zone_id=zone_id,
            entry_time=entry_data['entry_time'],
            exit_time=exit_time,
            duration_seconds=int(duration),
            engagement_score=engagement_score
        )
        db.add(dwell_record)
        db.commit()

        # Remove from active tracking
        del self.zone_entries[key]

    def get_current_dwell_time(self, tracking_id: str, zone_id: int) -> Optional[float]:
        """Get current dwell time for tracking_id in zone"""
        key = (tracking_id, zone_id)
        if key not in self.zone_entries:
            return None

        entry_time = self.zone_entries[key]['entry_time']
        return (datetime.now(UTC) - entry_time).total_seconds()


class ZoneDetector:
    """Detect which zone a person is in"""

    def __init__(self):
        self.zones: List[Dict] = []

    def load_zones(self, db: Session):
        """Load zones from database"""
        zone_records = db.query(Zone).filter(Zone.is_active == True).all()
        self.zones = []

        for zone in zone_records:
            # Parse polygon_points if it's a JSON string
            polygon_points = zone.polygon_points
            if isinstance(polygon_points, str):
                import json
                polygon_points = json.loads(polygon_points)
            
            self.zones.append({
                'id': zone.id,
                'name': zone.name,
                'type': zone.zone_type,
                'polygon': polygon_points,
                'color': zone.color,
                'max_capacity': zone.max_capacity
            })

        print(f"Loaded {len(self.zones)} active zones")

    def find_zone(self, point: Tuple[float, float]) -> Optional[int]:
        """Find which zone contains the point (normalized 0-1 coordinates)"""
        x, y = point

        for zone in self.zones:
            if self._point_in_polygon(x, y, zone['polygon']):
                return zone['id']

        return None

    def _point_in_polygon(self, x: float, y: float, polygon: List[List[float]]) -> bool:
        """Check if point is inside polygon using ray casting algorithm"""
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def get_zones(self) -> List[Dict]:
        """Get all zones"""
        return self.zones


class OccupancyCounter:
    """Track occupancy in zones and overall store"""

    def __init__(self):
        self.current_occupancy: Dict[Optional[int], Set[int]] = defaultdict(set)
        self.zone_detector = ZoneDetector()

    def update(
        self,
        detections: Dict[int, Tuple[float, float]],
        timestamp: datetime
    ) -> Dict[Optional[int], int]:
        """
        Update occupancy counts
        detections: {person_id: (norm_x, norm_y)}
        """
        new_occupancy = defaultdict(set)

        for person_id, position in detections.items():
            # Find zone
            zone_id = self.zone_detector.find_zone(position)

            if zone_id:
                new_occupancy[zone_id].add(person_id)

            # Track total store occupancy
            new_occupancy[None].add(person_id)

        self.current_occupancy = new_occupancy

        # Convert to counts
        counts = {zone_id: len(person_set) for zone_id, person_set in new_occupancy.items()}
        return counts

    def log_to_db(self, db: Session, timestamp: datetime):
        """Log current occupancy to database"""
        for zone_id, person_set in self.current_occupancy.items():
            log_entry = OccupancyLog(
                timestamp=timestamp,
                zone_id=zone_id,
                person_count=len(person_set),
                person_ids=list(person_set)
            )
            db.add(log_entry)

        db.commit()

    def get_occupancy(self, zone_id: Optional[int] = None) -> int:
        """Get current occupancy count for zone (None = total store)"""
        return len(self.current_occupancy.get(zone_id, set()))


class LineCrossingDetector:
    """Detect virtual line crossings using tracking_id"""

    def __init__(self):
        self.lines: List[Dict] = []
        self.last_positions: Dict[str, Tuple[float, float]] = {}  # {tracking_id: position}
        self.tracking_to_person: Dict[str, Optional[int]] = {}  # {tracking_id: person_id}
        self.crossing_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: {'in': 0, 'out': 0, 'total': 0})

    def load_lines(self, db: Session):
        """Load virtual lines from database"""
        line_records = db.query(VirtualLine).filter(VirtualLine.is_active == True).all()
        self.lines = []

        for line in line_records:
            # Parse start_point and end_point if they're JSON strings
            start_point = line.start_point
            end_point = line.end_point
            
            if isinstance(start_point, str):
                start_point = json.loads(start_point)
            if isinstance(end_point, str):
                end_point = json.loads(end_point)
            
            self.lines.append({
                'id': line.id,
                'name': line.name,
                'start': start_point,
                'end': end_point,
                'count_direction': line.count_direction,
                'color': line.color
            })

        print(f"Loaded {len(self.lines)} active virtual lines")

    def check_crossing(
        self,
        tracking_id: str,
        person_id: Optional[int],
        current_position: Tuple[float, float],
        timestamp: datetime
    ) -> Optional[Dict]:
        """Check if tracked body crossed any lines"""
        # Update person_id mapping
        if person_id is not None:
            self.tracking_to_person[tracking_id] = person_id

        if tracking_id not in self.last_positions:
            self.last_positions[tracking_id] = current_position
            return None

        last_pos = self.last_positions[tracking_id]
        crossing_event = None

        for line in self.lines:
            crossed, direction = self._detect_line_intersection(
                last_pos,
                current_position,
                (line['start']['x'], line['start']['y']),
                (line['end']['x'], line['end']['y'])
            )

            if crossed:
                self.crossing_counts[line['id']][direction] += 1
                self.crossing_counts[line['id']]['total'] += 1
                crossing_event = {
                    'line_id': line['id'],
                    'line_name': line['name'],
                    'direction': direction,
                    'point': current_position,
                    'tracking_id': tracking_id,
                    'person_id': person_id
                }
                break

        self.last_positions[tracking_id] = current_position
        return crossing_event

    def _detect_line_intersection(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        l1: Tuple[float, float],
        l2: Tuple[float, float]
    ) -> Tuple[bool, str]:
        """
        Detect if line segment p1-p2 intersects with line segment l1-l2
        Returns (crossed, direction)
        """
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        # Check if segments intersect
        if not (ccw(p1, l1, l2) != ccw(p2, l1, l2) and ccw(p1, p2, l1) != ccw(p1, p2, l2)):
            return False, ""

        # Determine direction (in or out) based on cross product
        cross = (p2[0] - p1[0]) * (l2[1] - l1[1]) - (p2[1] - p1[1]) * (l2[0] - l1[0])
        direction = "in" if cross > 0 else "out"

        return True, direction

    def log_crossing(self, db: Session, crossing_event: Dict, timestamp: datetime):
        """Log crossing event to database"""
        tracking_id = crossing_event.get('tracking_id')
        person_id = crossing_event.get('person_id') or self.tracking_to_person.get(tracking_id)

        event = LineCrossingEvent(
            person_id=person_id,
            body_tracking_id=tracking_id,
            line_id=crossing_event['line_id'],
            timestamp=timestamp,
            direction=crossing_event['direction'],
            crossing_point=crossing_event['point']
        )
        db.add(event)
        db.commit()

    def get_counts(self, line_id: int) -> Dict[str, int]:
        """Get crossing counts for a line"""
        return self.crossing_counts.get(line_id, {'in': 0, 'out': 0})


class HeatmapGenerator:
    """Generate traffic heatmaps"""

    def __init__(self, width: int = 1280, height: int = 720, resolution: int = 20):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.grid_width = width // resolution
        self.grid_height = height // resolution
        self.heat_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)

    def add_detection(self, position: Tuple[float, float], weight: float = 1.0):
        """Add detection to heatmap (normalized coordinates)"""
        # Convert normalized to pixel coordinates
        x = int(position[0] * self.width)
        y = int(position[1] * self.height)

        # Convert to grid coordinates
        grid_x = min(x // self.resolution, self.grid_width - 1)
        grid_y = min(y // self.resolution, self.grid_height - 1)

        # Add heat
        self.heat_grid[grid_y, grid_x] += weight

    def generate_heatmap_overlay(self, alpha: float = 0.5) -> np.ndarray:
        """Generate heatmap overlay image"""
        if self.heat_grid.max() == 0:
            # Return transparent image if no data
            return np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Apply gaussian blur for smoothing
        blurred = gaussian_filter(self.heat_grid, sigma=2.0)

        # Normalize to 0-255
        normalized = (blurred / blurred.max() * 255).astype(np.uint8)

        # Apply colormap (blue -> green -> yellow -> red)
        heatmap = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

        # Resize to original dimensions
        heatmap_full = cv2.resize(heatmap, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

        # Add alpha channel
        heatmap_rgba = cv2.cvtColor(heatmap_full, cv2.COLOR_BGR2BGRA)
        # Resize normalized alpha to match full image dimensions
        alpha_channel = cv2.resize(normalized, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        heatmap_rgba[:, :, 3] = (alpha * alpha_channel).astype(np.uint8)

        return heatmap_rgba

    def save_to_db(self, db: Session, time_bucket: str):
        """Save heatmap to database"""
        import pickle

        heatmap_data = HeatmapData(
            time_bucket=time_bucket,
            heatmap_array=pickle.dumps(self.heat_grid),
            max_intensity=float(self.heat_grid.max()),
            timestamp=datetime.now(UTC)
        )
        db.add(heatmap_data)
        db.commit()

    def reset(self):
        """Reset heatmap grid"""
        self.heat_grid = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)


class InteractionTracker:
    """
    Track product interactions with engagement scoring
    Integrates with hand detection and zone detection
    """

    def __init__(self):
        # Active interactions: (tracking_id, zone_id) -> interaction_data
        self.active_interactions: Dict[Tuple[str, int], Dict] = {}
        self.session_ids: Dict[str, str] = {}  # {tracking_id: session_uuid}
        self.tracking_to_person: Dict[str, Optional[int]] = {}

    def start_interaction(
        self,
        tracking_id: str,
        person_id: Optional[int],
        zone_id: int,
        interaction_type: str,
        hand_position: Tuple[float, float],
        gesture_type: str,
        timestamp: datetime
    ):
        """Start tracking a new interaction"""
        # Get or create session ID
        if tracking_id not in self.session_ids:
            self.session_ids[tracking_id] = str(uuid.uuid4())

        # Update person mapping
        if person_id is not None:
            self.tracking_to_person[tracking_id] = person_id

        key = (tracking_id, zone_id)
        self.active_interactions[key] = {
            'person_id': person_id,
            'zone_id': zone_id,
            'interaction_type': interaction_type,
            'hand_position': hand_position,
            'gesture_type': gesture_type,
            'start_time': timestamp,
            'last_update': timestamp,
            'session_id': self.session_ids[tracking_id]
        }

    def update_interaction(
        self,
        tracking_id: str,
        zone_id: int,
        interaction_type: str,
        hand_position: Tuple[float, float],
        gesture_type: str,
        timestamp: datetime
    ) -> Optional[float]:
        """Update existing interaction and return duration"""
        key = (tracking_id, zone_id)

        if key not in self.active_interactions:
            return None

        interaction = self.active_interactions[key]
        interaction['interaction_type'] = interaction_type
        interaction['hand_position'] = hand_position
        interaction['gesture_type'] = gesture_type
        interaction['last_update'] = timestamp

        duration = (timestamp - interaction['start_time']).total_seconds()
        return duration

    def end_interaction(
        self,
        db: Session,
        tracking_id: str,
        zone_id: int,
        timestamp: datetime
    ):
        """End interaction and save to database"""
        key = (tracking_id, zone_id)

        if key not in self.active_interactions:
            return

        interaction = self.active_interactions[key]
        duration = (timestamp - interaction['start_time']).total_seconds()

        person_id = interaction.get('person_id') or self.tracking_to_person.get(tracking_id)

        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(
            interaction['interaction_type'],
            duration,
            interaction['gesture_type']
        )

        # Save to database
        db_interaction = ProductInteraction(
            person_id=person_id,
            zone_id=zone_id,
            timestamp=interaction['start_time'],
            interaction_type=interaction['interaction_type'],
            duration_seconds=duration,
            engagement_score=engagement_score,
            hand_position={
                'x': interaction['hand_position'][0],
                'y': interaction['hand_position'][1]
            },
            gesture_type=interaction['gesture_type']
        )

        db.add(db_interaction)
        db.commit()

        # Remove from active tracking
        del self.active_interactions[key]

    def _calculate_engagement_score(
        self,
        interaction_type: str,
        duration: float,
        gesture_type: str
    ) -> float:
        """Calculate engagement score (0-1) based on interaction characteristics"""
        base_scores = {
            'touching': 0.3,
            'reaching': 0.4,
            'picking_up': 0.7,
            'examining': 0.9,
            'putting_back': 0.5
        }

        score = base_scores.get(interaction_type, 0.5)

        # Boost for specific gestures
        if gesture_type == 'grabbing':
            score += 0.1
        elif gesture_type == 'pointing':
            score += 0.05

        # Boost for longer duration (up to 30 seconds)
        score += min(0.2, duration / 150.0)

        return min(1.0, score)

    def get_active_interactions(self) -> List[Dict]:
        """Get all active interactions"""
        return [
            {
                'tracking_id': key[0],
                'zone_id': key[1],
                **data
            }
            for key, data in self.active_interactions.items()
        ]

    def cleanup_old_interactions(self, max_age_seconds: float = 10.0):
        """Remove stale interactions"""
        current_time = datetime.now(UTC)
        keys_to_remove = []

        for key, interaction in self.active_interactions.items():
            age = (current_time - interaction['last_update']).total_seconds()
            if age > max_age_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.active_interactions[key]


class QueueDetector:
    """Detect queue formations"""

    def __init__(self, queue_threshold_distance: float = 0.05, min_queue_length: int = 3):
        self.queue_threshold = queue_threshold_distance  # Normalized distance
        self.min_queue_length = min_queue_length

    def detect_queues(
        self,
        person_positions: Dict[int, Tuple[float, float]],
        zone_detector: ZoneDetector
    ) -> List[Dict]:
        """
        Detect queue formations
        person_positions: {person_id: (norm_x, norm_y)}
        """
        if len(person_positions) < self.min_queue_length:
            return []

        # Cluster people based on proximity
        clusters = self._cluster_by_proximity(person_positions)

        # Filter for queue-like formations
        queues = []
        for cluster in clusters:
            if len(cluster) >= self.min_queue_length:
                if self._is_linear_formation(cluster):
                    # Determine which zone this queue is in
                    zone_id = self._get_queue_zone(cluster, zone_detector)

                    queues.append({
                        'zone_id': zone_id,
                        'people': cluster,
                        'length': len(cluster),
                        'positions': [person_positions[pid] for pid in cluster]
                    })

        return queues

    def _cluster_by_proximity(self, positions: Dict[int, Tuple[float, float]]) -> List[List[int]]:
        """Cluster people based on proximity"""
        clusters = []
        assigned = set()

        for person_id, pos in positions.items():
            if person_id in assigned:
                continue

            cluster = [person_id]
            assigned.add(person_id)

            # Find nearby people
            for other_id, other_pos in positions.items():
                if other_id in assigned:
                    continue

                distance = np.sqrt((pos[0] - other_pos[0])**2 + (pos[1] - other_pos[1])**2)
                if distance < self.queue_threshold:
                    cluster.append(other_id)
                    assigned.add(other_id)

            if len(cluster) >= self.min_queue_length:
                clusters.append(cluster)

        return clusters

    def _is_linear_formation(self, cluster: List[int]) -> bool:
        """Check if cluster forms a linear pattern (queue-like)"""
        # Simplified check - in production, use PCA or line fitting
        return len(cluster) >= self.min_queue_length

    def _get_queue_zone(self, cluster: List[int], zone_detector: ZoneDetector) -> Optional[int]:
        """Determine which zone the queue is in"""
        # Use first person's position
        # In production, use centroid of cluster
        return None

    def log_queue_metrics(self, db: Session, queue_data: Dict, timestamp: datetime):
        """Log queue metrics to database"""
        metrics = QueueMetrics(
            zone_id=queue_data.get('zone_id'),
            timestamp=timestamp,
            queue_length=queue_data['length'],
            people_in_queue=queue_data['people']
        )
        db.add(metrics)
        db.commit()
