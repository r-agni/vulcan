"""
Alert Manager - Manages alert queue, delivery, and lifecycle
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import threading
from .alert_types import Alert, AlertPriority, AlertRecipient


class AlertManager:
    """Manage alert queue and delivery"""
    
    def __init__(self, max_queue_size: int = 50, alert_expiry_seconds: int = 600):
        self.active_alerts: Dict[str, Alert] = {}  # {alert_id: Alert}
        self.alert_history: List[Alert] = []
        self.max_queue_size = max_queue_size
        self.alert_expiry_seconds = alert_expiry_seconds
        
        # Deduplication tracking
        self.recent_alert_signatures: Dict[str, datetime] = {}
        self.signature_expiry_seconds = 300  # 5 minutes
        
        # Priority queue for display
        self.priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3
        }
        
        self.lock = threading.Lock()
    
    def add_alerts(self, alerts: List[Alert]) -> List[Alert]:
        """
        Add multiple alerts to the queue with deduplication
        Returns list of alerts that were actually added
        """
        added_alerts = []
        
        with self.lock:
            for alert in alerts:
                if self._should_add_alert(alert):
                    # Set expiry time
                    if not alert.expires_at:
                        alert.expires_at = datetime.now() + timedelta(seconds=self.alert_expiry_seconds)
                    
                    self.active_alerts[alert.id] = alert
                    added_alerts.append(alert)
                    
                    # Update deduplication signature
                    signature = self._get_alert_signature(alert)
                    self.recent_alert_signatures[signature] = datetime.now()
            
            # Cleanup expired alerts
            self._cleanup_expired_alerts()
            
            # Enforce max queue size
            if len(self.active_alerts) > self.max_queue_size:
                self._trim_queue()
        
        return added_alerts
    
    def _should_add_alert(self, alert: Alert) -> bool:
        """Check if alert should be added (deduplication logic)"""
        # Check if identical alert exists in active alerts
        if alert.id in self.active_alerts:
            return False
        
        # Check signature-based deduplication
        signature = self._get_alert_signature(alert)
        if signature in self.recent_alert_signatures:
            last_time = self.recent_alert_signatures[signature]
            if (datetime.now() - last_time).total_seconds() < self.signature_expiry_seconds:
                return False  # Too soon to send similar alert
        
        return True
    
    def _get_alert_signature(self, alert: Alert) -> str:
        """Generate signature for deduplication"""
        # Signature based on category, recipient, zone, and general content
        return f"{alert.category.value}_{alert.recipient.value}_{alert.zone_id}_{alert.title[:50]}"
    
    def _cleanup_expired_alerts(self):
        """Remove expired alerts from active queue"""
        current_time = datetime.now()
        expired_ids = []
        
        for alert_id, alert in self.active_alerts.items():
            if alert.expires_at and current_time > alert.expires_at:
                expired_ids.append(alert_id)
                # Move to history
                alert.status = "expired"
                self.alert_history.append(alert)
        
        for alert_id in expired_ids:
            del self.active_alerts[alert_id]
        
        # Cleanup old signature tracking
        old_signatures = []
        for sig, timestamp in self.recent_alert_signatures.items():
            if (current_time - timestamp).total_seconds() > self.signature_expiry_seconds * 2:
                old_signatures.append(sig)
        
        for sig in old_signatures:
            del self.recent_alert_signatures[sig]
    
    def _trim_queue(self):
        """Trim queue to max size, keeping highest priority alerts"""
        if len(self.active_alerts) <= self.max_queue_size:
            return
        
        # Sort by priority and timestamp
        sorted_alerts = sorted(
            self.active_alerts.values(),
            key=lambda a: (self.priority_order[a.priority], a.timestamp),
            reverse=False  # Lower priority number = higher priority
        )
        
        # Keep top alerts
        alerts_to_keep = sorted_alerts[:self.max_queue_size]
        keep_ids = {alert.id for alert in alerts_to_keep}
        
        # Remove others
        alerts_to_remove = [aid for aid in self.active_alerts.keys() if aid not in keep_ids]
        for alert_id in alerts_to_remove:
            alert = self.active_alerts[alert_id]
            alert.status = "expired"
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "user") -> bool:
        """Acknowledge an alert"""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = "acknowledged"
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                
                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                return True
        return False
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert without acknowledgment"""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = "dismissed"
                
                # Move to history
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                return True
        return False
    
    def get_active_alerts(
        self,
        recipient_filter: Optional[AlertRecipient] = None,
        priority_filter: Optional[AlertPriority] = None
    ) -> List[Alert]:
        """Get active alerts with optional filtering"""
        with self.lock:
            self._cleanup_expired_alerts()
            
            alerts = list(self.active_alerts.values())
            
            # Apply filters
            if recipient_filter:
                alerts = [a for a in alerts if a.recipient == recipient_filter or a.recipient == AlertRecipient.BOTH]
            
            if priority_filter:
                alerts = [a for a in alerts if a.priority == priority_filter]
            
            # Sort by priority and timestamp
            alerts.sort(
                key=lambda a: (self.priority_order[a.priority], a.timestamp),
                reverse=False
            )
            
            return alerts
    
    def get_alerts_for_dashboard(self, limit: int = 10) -> List[Dict]:
        """Get alerts formatted for dashboard display"""
        alerts = self.get_active_alerts()[:limit]
        return [alert.to_dict() for alert in alerts]
    
    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get specific alert by ID"""
        with self.lock:
            return self.active_alerts.get(alert_id)
    
    def get_alert_statistics(self) -> Dict:
        """Get statistics about alerts"""
        with self.lock:
            total_active = len(self.active_alerts)
            
            by_priority = defaultdict(int)
            by_category = defaultdict(int)
            by_recipient = defaultdict(int)
            
            for alert in self.active_alerts.values():
                by_priority[alert.priority.value] += 1
                by_category[alert.category.value] += 1
                by_recipient[alert.recipient.value] += 1
            
            return {
                'total_active': total_active,
                'by_priority': dict(by_priority),
                'by_category': dict(by_category),
                'by_recipient': dict(by_recipient),
                'total_historical': len(self.alert_history)
            }
    
    def clear_all_alerts(self):
        """Clear all active alerts (for testing/reset)"""
        with self.lock:
            for alert in self.active_alerts.values():
                alert.status = "cleared"
                self.alert_history.append(alert)
            self.active_alerts.clear()
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get alert history"""
        with self.lock:
            recent_history = self.alert_history[-limit:]
            return [alert.to_dict() for alert in reversed(recent_history)]
    
    def get_alerts_by_zone(self, zone_id: int) -> List[Alert]:
        """Get active alerts for a specific zone"""
        with self.lock:
            return [alert for alert in self.active_alerts.values() if alert.zone_id == zone_id]
    
    def get_alerts_by_person(self, person_id: int) -> List[Alert]:
        """Get active alerts for a specific person"""
        with self.lock:
            return [alert for alert in self.active_alerts.values() if alert.person_id == person_id]
    
    def has_critical_alerts(self) -> bool:
        """Check if there are any critical alerts"""
        with self.lock:
            return any(alert.priority == AlertPriority.CRITICAL for alert in self.active_alerts.values())
    
    def get_highest_priority_alert(self) -> Optional[Alert]:
        """Get the highest priority active alert"""
        alerts = self.get_active_alerts()
        return alerts[0] if alerts else None

    def assign_alert_to_staff(
        self,
        db,
        alert_id: str,
        staff_coordinator,
        zone_positions: Dict[int, tuple]
    ) -> Optional[int]:
        """
        Assign alert to appropriate staff member

        Args:
            db: Database session
            alert_id: Alert ID to assign
            staff_coordinator: StaffCoordinator instance
            zone_positions: Dict mapping zone_id to (x, y) position

        Returns:
            staff_id of assigned person, or None if no one available
        """
        alert = self.get_alert_by_id(alert_id)

        if not alert:
            return None

        staff_id = staff_coordinator.assign_alert_to_staff(
            db, alert, zone_positions
        )

        if staff_id:
            # Update alert context with assignment
            if not alert.context_data:
                alert.context_data = {}
            alert.context_data['assigned_to'] = staff_id
            alert.context_data['assigned_at'] = datetime.now().isoformat()

        return staff_id
