"""
Staff Coordinator Agent
Intelligently assigns alerts to staff and optimizes distribution
"""

from google import genai
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from dataclasses import dataclass
import json
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import StaffMember, StaffLocation, AlertAssignment, StaffPerformanceMetrics


@dataclass
class StaffStatus:
    """Current status of a staff member"""
    staff_id: int
    name: str
    role: str
    current_zone_id: Optional[int]
    is_available: bool
    current_workload: int
    distance_to_zone: float
    expertise_score: float
    avg_response_time: float


class StaffCoordinator:
    """Manage staff assignments and optimization"""

    def __init__(self, api_key: str):
        """
        Initialize Staff Coordinator

        Args:
            api_key: Gemini API key for AI-powered decision making
        """
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        print("[Staff Coordinator] Initialized with Gemini 2.5 Flash")

    def assign_alert_to_staff(
        self,
        db: Session,
        alert,
        zone_positions: Dict[int, Tuple[float, float]]
    ) -> Optional[int]:
        """
        Assign alert to best available staff member

        Args:
            db: Database session
            alert: Alert object to assign
            zone_positions: Dict mapping zone_id to (x, y) position

        Returns:
            staff_id of assigned person, or None if no one available
        """
        # Get available staff
        available_staff = self._get_available_staff(db)

        if not available_staff:
            print("[Staff Coordinator] No available staff for assignment")
            return None

        # Score each staff member
        staff_scores = []
        for staff in available_staff:
            score = self._calculate_assignment_score(
                db, staff, alert, zone_positions
            )
            staff_scores.append((staff.id, score, staff.name))

        # Sort by score (highest first)
        staff_scores.sort(key=lambda x: x[1], reverse=True)

        print(f"[Staff Coordinator] Candidate scores: {[(name, round(score, 2)) for _, score, name in staff_scores[:3]]}")

        # Use Gemini for final decision if multiple good candidates
        if len([s for s in staff_scores if s[1] > 0.7]) > 1:
            best_staff_id = self._gemini_select_staff(
                db, alert, available_staff, staff_scores
            )
        else:
            best_staff_id = staff_scores[0][0]

        # Create assignment
        assignment = AlertAssignment(
            alert_id=alert.id,
            staff_id=best_staff_id,
            assigned_at=datetime.now(UTC)
        )
        db.add(assignment)
        db.commit()

        assigned_name = next((name for sid, _, name in staff_scores if sid == best_staff_id), "Unknown")
        print(f"[Staff Coordinator] Assigned alert '{alert.title}' to {assigned_name} (ID: {best_staff_id})")

        return best_staff_id

    def _get_available_staff(self, db: Session) -> List[StaffMember]:
        """Get currently available staff members"""
        now = datetime.now(UTC)

        # Get on-duty staff
        staff = db.query(StaffMember).filter(
            StaffMember.is_on_duty == True
        ).all()

        # Filter staff who are on duty and within shift time
        on_shift = []
        for member in staff:
            # If no shift times set, assume available
            if not member.shift_start or not member.shift_end:
                on_shift.append(member)
            elif member.shift_start <= now <= member.shift_end:
                on_shift.append(member)

        # Filter by availability
        available = []
        for member in on_shift:
            # Get latest location
            latest_location = db.query(StaffLocation).filter(
                StaffLocation.staff_id == member.id
            ).order_by(StaffLocation.timestamp.desc()).first()

            # If no location or marked available, consider them available
            if not latest_location or latest_location.is_available:
                available.append(member)

        return available

    def _calculate_assignment_score(
        self,
        db: Session,
        staff: StaffMember,
        alert,
        zone_positions: Dict[int, Tuple[float, float]]
    ) -> float:
        """
        Calculate suitability score for assigning this alert to this staff
        Factors: proximity, expertise, workload, response history

        Returns:
            Score from 0-1 (higher is better)
        """
        score = 0.0

        # 1. Proximity (40% weight)
        distance = self._calculate_distance_to_zone(
            db, staff.id, alert.zone_id, zone_positions
        )
        proximity_score = max(0, 1 - distance)  # Closer = higher
        score += proximity_score * 0.4

        # 2. Expertise (30% weight)
        expertise = self._get_expertise_score(db, staff.id, alert.category.value)
        score += expertise * 0.3

        # 3. Workload (20% weight)
        workload = self._get_current_workload(db, staff.id)
        workload_score = max(0, 1 - (workload / 5))  # Fewer tasks = higher
        score += workload_score * 0.2

        # 4. Response history (10% weight)
        response_score = self._get_response_score(db, staff.id)
        score += response_score * 0.1

        return score

    def _calculate_distance_to_zone(
        self,
        db: Session,
        staff_id: int,
        target_zone_id: Optional[int],
        zone_positions: Dict[int, Tuple[float, float]]
    ) -> float:
        """Calculate normalized distance from staff to zone"""
        if not target_zone_id or target_zone_id not in zone_positions:
            return 0.5  # Medium distance if unknown

        # Get staff location
        location = db.query(StaffLocation).filter(
            StaffLocation.staff_id == staff_id
        ).order_by(StaffLocation.timestamp.desc()).first()

        if not location:
            return 0.5

        # Calculate Euclidean distance
        target_x, target_y = zone_positions[target_zone_id]
        distance = ((location.x_position - target_x)**2 +
                   (location.y_position - target_y)**2)**0.5

        return distance

    def _get_expertise_score(
        self,
        db: Session,
        staff_id: int,
        alert_category: str
    ) -> float:
        """Get staff expertise for this alert category"""
        metrics = db.query(StaffPerformanceMetrics).filter(
            StaffPerformanceMetrics.staff_id == staff_id
        ).order_by(StaffPerformanceMetrics.date.desc()).first()

        if not metrics:
            return 0.5  # Default medium expertise

        category_scores = {
            "customer_service": metrics.customer_service_score,
            "queue_management": metrics.queue_management_score,
            "operations": 0.7,  # Default
        }

        return category_scores.get(alert_category, 0.5) or 0.5

    def _get_current_workload(self, db: Session, staff_id: int) -> int:
        """Get number of active assignments for staff"""
        active_count = db.query(AlertAssignment).filter(
            AlertAssignment.staff_id == staff_id,
            AlertAssignment.completed_at == None
        ).count()

        return active_count

    def _get_response_score(self, db: Session, staff_id: int) -> float:
        """Get staff's historical response quality (0-1)"""
        recent_assignments = db.query(AlertAssignment).filter(
            AlertAssignment.staff_id == staff_id,
            AlertAssignment.completed_at != None
        ).order_by(AlertAssignment.assigned_at.desc()).limit(10).all()

        if not recent_assignments:
            return 0.7  # Default good score for new staff

        success_count = len([a for a in recent_assignments
                           if a.outcome == "success"])

        return success_count / len(recent_assignments)

    def _gemini_select_staff(
        self,
        db: Session,
        alert,
        staff_list: List[StaffMember],
        scores: List[Tuple[int, float, str]]
    ) -> int:
        """Use Gemini for nuanced staff selection"""
        # Build context
        staff_data = []
        for staff in staff_list:
            score_tuple = next((s for s in scores if s[0] == staff.id), None)
            if not score_tuple:
                continue

            score = score_tuple[1]

            location = db.query(StaffLocation).filter(
                StaffLocation.staff_id == staff.id
            ).order_by(StaffLocation.timestamp.desc()).first()

            staff_data.append({
                "id": staff.id,
                "name": staff.name,
                "role": staff.role,
                "score": round(score, 2),
                "current_zone": location.zone_id if location else None,
                "workload": self._get_current_workload(db, staff.id)
            })

        prompt = f"""
        Select the best staff member to handle this customer service alert:

        ALERT:
        - Title: {alert.title}
        - Category: {alert.category.value}
        - Priority: {alert.priority.value}
        - Zone: {alert.zone_name or 'Unknown'}
        - Person: {alert.person_id or 'Unknown'}

        AVAILABLE STAFF:
        {json.dumps(staff_data, indent=2)}

        Consider:
        - Alert urgency and staff proximity
        - Staff expertise and workload
        - Customer needs (if high-value, send experienced staff)

        Respond with ONLY the staff ID number (e.g., "5")
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            selected_id = int(response.text.strip())

            # Validate selection
            if selected_id in [s.id for s in staff_list]:
                print(f"[Staff Coordinator] Gemini selected staff ID: {selected_id}")
                return selected_id
            else:
                # Fallback to highest scored
                print(f"[Staff Coordinator] Gemini selected invalid ID, using highest score")
                return scores[0][0]

        except Exception as e:
            print(f"[Staff Coordinator] Gemini selection error: {e}, using highest score")
            return scores[0][0]

    def balance_staff_distribution(
        self,
        db: Session,
        zone_occupancies: Dict[int, int],
        zone_positions: Dict[int, Tuple[float, float]]
    ) -> List[Dict]:
        """
        Suggest staff movements to balance coverage

        Args:
            db: Database session
            zone_occupancies: Dict mapping zone_id to customer count
            zone_positions: Dict mapping zone_id to (x, y) position

        Returns:
            List of recommendations [{"staff_id": X, "target_zone": Y, "reason": "..."}]
        """
        recommendations = []

        # Get current staff distribution
        staff_zones = self._get_staff_distribution(db)

        # Identify understaffed zones
        for zone_id, occupancy in zone_occupancies.items():
            staff_count = len([s for s in staff_zones if s['zone_id'] == zone_id])

            # Rule: 1 staff per 5 customers
            needed_staff = max(1, occupancy // 5)

            if staff_count < needed_staff:
                # Find nearest available staff
                available = self._get_available_staff(db)

                for staff in available:
                    if self._get_current_workload(db, staff.id) == 0:
                        distance = self._calculate_distance_to_zone(
                            db, staff.id, zone_id, zone_positions
                        )

                        recommendations.append({
                            "staff_id": staff.id,
                            "staff_name": staff.name,
                            "target_zone": zone_id,
                            "reason": f"Zone has {occupancy} customers but only {staff_count} staff",
                            "distance": round(distance, 2)
                        })
                        break

        return recommendations

    def _get_staff_distribution(self, db: Session) -> List[Dict]:
        """Get current zone distribution of staff"""
        on_duty = db.query(StaffMember).filter(
            StaffMember.is_on_duty == True
        ).all()

        distribution = []
        for staff in on_duty:
            location = db.query(StaffLocation).filter(
                StaffLocation.staff_id == staff.id
            ).order_by(StaffLocation.timestamp.desc()).first()

            if location:
                distribution.append({
                    "staff_id": staff.id,
                    "zone_id": location.zone_id
                })

        return distribution

    def track_assignment_outcome(
        self,
        db: Session,
        alert_id: str,
        outcome: str,
        staff_notes: Optional[str] = None,
        customer_satisfaction: Optional[int] = None
    ):
        """
        Record outcome of alert assignment for learning

        Args:
            db: Database session
            alert_id: Alert ID
            outcome: "success", "ignored", or "escalated"
            staff_notes: Optional notes from staff
            customer_satisfaction: Optional rating 1-5
        """
        assignment = db.query(AlertAssignment).filter(
            AlertAssignment.alert_id == alert_id
        ).first()

        if not assignment:
            return

        # Update assignment
        assignment.completed_at = datetime.now(UTC)
        assignment.outcome = outcome
        assignment.staff_notes = staff_notes
        assignment.customer_satisfaction_score = customer_satisfaction

        if assignment.accepted_at:
            assignment.completion_time_seconds = (
                assignment.completed_at - assignment.accepted_at
            ).total_seconds()

        db.commit()

        # Update staff metrics
        self._update_staff_metrics(db, assignment)

        print(f"[Staff Coordinator] Tracked outcome '{outcome}' for alert {alert_id}")

    def _update_staff_metrics(self, db: Session, assignment: AlertAssignment):
        """Update staff performance metrics after assignment completion"""
        today = datetime.now(UTC).date()

        # Get or create today's metrics
        metrics = db.query(StaffPerformanceMetrics).filter(
            StaffPerformanceMetrics.staff_id == assignment.staff_id,
            StaffPerformanceMetrics.date >= datetime.combine(today, datetime.min.time())
        ).first()

        if not metrics:
            metrics = StaffPerformanceMetrics(
                staff_id=assignment.staff_id,
                date=datetime.now(UTC),
                alerts_assigned=0,
                alerts_completed=0,
                alerts_ignored=0,
                avg_response_time_seconds=0,
                avg_completion_time_seconds=0,
                customer_service_score=0.7,
                queue_management_score=0.7,
                technical_support_score=0.7
            )
            db.add(metrics)

        # Update counts
        metrics.alerts_assigned += 1

        if assignment.outcome == "success":
            metrics.alerts_completed += 1
        elif assignment.outcome == "ignored":
            metrics.alerts_ignored += 1

        # Update response times (rolling average)
        if assignment.response_time_seconds:
            if metrics.avg_response_time_seconds:
                metrics.avg_response_time_seconds = (
                    metrics.avg_response_time_seconds * 0.8 +
                    assignment.response_time_seconds * 0.2
                )
            else:
                metrics.avg_response_time_seconds = assignment.response_time_seconds

        db.commit()
        print(f"[Staff Coordinator] Updated metrics for staff {assignment.staff_id}")
