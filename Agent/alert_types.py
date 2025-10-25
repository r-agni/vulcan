"""
Alert Type Definitions
Defines alert priorities, categories, recipients, and data structures
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCategory(Enum):
    """Alert categories"""
    CUSTOMER_SERVICE = "customer_service"
    QUEUE_MANAGEMENT = "queue_management"
    SECURITY = "security"
    OPERATIONS = "operations"
    CAPACITY = "capacity"
    SYSTEM = "system"


class AlertRecipient(Enum):
    """Who should receive the alert"""
    SALESPERSON = "salesperson"
    MANAGER = "manager"
    BOTH = "both"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    message: str
    priority: AlertPriority
    category: AlertCategory
    recipient: AlertRecipient
    timestamp: datetime
    status: str = "active"  # active, acknowledged, expired
    person_id: Optional[int] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    # Person-specific details for salesperson alerts
    person_details: Optional[Dict[str, Any]] = None  # Demographics, appearance, behavior history
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'priority': self.priority.value,
            'category': self.category.value,
            'recipient': self.recipient.value,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'person_id': self.person_id,
            'zone_id': self.zone_id,
            'zone_name': self.zone_name,
            'context_data': self.context_data,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'person_details': self.person_details
        }
    
    def get_color(self) -> str:
        """Get color code for alert priority"""
        color_map = {
            AlertPriority.LOW: "#4A90E2",
            AlertPriority.MEDIUM: "#F5A623",
            AlertPriority.HIGH: "#E94B3C",
            AlertPriority.CRITICAL: "#D0021B"
        }
        return color_map.get(self.priority, "#4A90E2")
    
    def get_icon(self) -> str:
        """Get emoji icon for alert category"""
        icon_map = {
            AlertCategory.CUSTOMER_SERVICE: "🛎️",
            AlertCategory.QUEUE_MANAGEMENT: "⏱️",
            AlertCategory.SECURITY: "🔒",
            AlertCategory.OPERATIONS: "⚙️",
            AlertCategory.CAPACITY: "👥",
            AlertCategory.SYSTEM: "💻"
        }
        return icon_map.get(self.category, "ℹ️")
