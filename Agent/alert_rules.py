"""
Alert Business Rules
Defines conditions and thresholds for triggering alerts
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .alert_types import AlertPriority, AlertCategory, AlertRecipient


class AlertRules:
    """Business rules for alert generation"""
    
    # Dwell time thresholds (seconds)
    DWELL_TIME_INITIAL_INTEREST = 120      # 2 minutes - initial interest
    DWELL_TIME_ASSISTANCE_THRESHOLD = 300  # 5 minutes - may need help
    DWELL_TIME_EXTENDED_THRESHOLD = 600    # 10 minutes - definitely interested
    DWELL_TIME_UNUSUAL_THRESHOLD = 900     # 15 minutes - unusual pattern
    
    # Queue thresholds
    QUEUE_LENGTH_WARNING = 5
    QUEUE_LENGTH_CRITICAL = 7
    QUEUE_WAIT_TIME_WARNING = 180  # 3 minutes
    QUEUE_WAIT_TIME_CRITICAL = 300  # 5 minutes
    QUEUE_ABANDONMENT_THRESHOLD = 3  # 3 abandonments in 10 minutes
    
    # Occupancy thresholds
    OCCUPANCY_WARNING_PERCENT = 0.75  # 75%
    OCCUPANCY_CRITICAL_PERCENT = 0.90  # 90%
    
    # Customer behavior patterns
    CONFUSED_BEHAVIOR_INDICATORS = [
        "looking around",
        "searching",
        "confused",
        "uncertain",
        "hesitant",
        "frustrated",
        "difficulty finding"
    ]
    
    ASSISTANCE_NEEDED_INDICATORS = [
        "examining multiple products",
        "comparing items",
        "reading labels repeatedly",
        "looking for assistance",
        "waiting near counter"
    ]
    
    HIGH_VALUE_INDICATORS = [
        "premium section",
        "expensive products",
        "prolonged examination",
        "returning customer",
        "VIP"
    ]
    
    @staticmethod
    def should_alert_long_dwell(dwell_time: float, zone_type: str) -> Optional[Dict[str, Any]]:
        """Check if long dwell time should trigger alert"""
        if dwell_time >= AlertRules.DWELL_TIME_UNUSUAL_THRESHOLD:
            return {
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.OPERATIONS,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'Unusual dwell time: {int(dwell_time//60)} minutes'
            }
        elif dwell_time >= AlertRules.DWELL_TIME_EXTENDED_THRESHOLD:
            return {
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': f'High interest customer: {int(dwell_time//60)} minutes in zone',
                'salesperson_priority': True
            }
        elif dwell_time >= AlertRules.DWELL_TIME_ASSISTANCE_THRESHOLD:
            return {
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': f'Customer may need assistance: {int(dwell_time//60)} minutes in zone',
                'salesperson_priority': True
            }
        elif dwell_time >= AlertRules.DWELL_TIME_INITIAL_INTEREST:
            return {
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': f'Customer showing interest: {int(dwell_time//60)} minutes in zone',
                'salesperson_priority': True
            }
        return None
    
    @staticmethod
    def should_alert_queue(queue_length: int, avg_wait_time: Optional[float]) -> Optional[Dict[str, Any]]:
        """Check if queue metrics should trigger alert"""
        if queue_length >= AlertRules.QUEUE_LENGTH_CRITICAL:
            return {
                'priority': AlertPriority.CRITICAL,
                'category': AlertCategory.QUEUE_MANAGEMENT,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'Critical queue length: {queue_length} customers waiting'
            }
        elif queue_length >= AlertRules.QUEUE_LENGTH_WARNING:
            return {
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.QUEUE_MANAGEMENT,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'Queue building up: {queue_length} customers'
            }
        
        if avg_wait_time and avg_wait_time >= AlertRules.QUEUE_WAIT_TIME_CRITICAL:
            return {
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.QUEUE_MANAGEMENT,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'Long wait times: average {int(avg_wait_time//60)} minutes'
            }
        
        return None
    
    @staticmethod
    def should_alert_occupancy(current: int, capacity: int) -> Optional[Dict[str, Any]]:
        """Check if occupancy should trigger alert"""
        if capacity <= 0:
            return None
        
        occupancy_percent = current / capacity
        
        if occupancy_percent >= AlertRules.OCCUPANCY_CRITICAL_PERCENT:
            return {
                'priority': AlertPriority.CRITICAL,
                'category': AlertCategory.CAPACITY,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'Near capacity: {current}/{capacity} ({int(occupancy_percent*100)}%)'
            }
        elif occupancy_percent >= AlertRules.OCCUPANCY_WARNING_PERCENT:
            return {
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.CAPACITY,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'High occupancy: {current}/{capacity} ({int(occupancy_percent*100)}%)'
            }
        
        return None
    
    @staticmethod
    def analyze_behavior_text(analysis_text: str) -> List[Dict[str, Any]]:
        """Analyze behavior text for alert triggers"""
        alerts = []
        text_lower = analysis_text.lower()
        
        # Check for confused/needs assistance indicators
        confusion_score = sum(1 for indicator in AlertRules.CONFUSED_BEHAVIOR_INDICATORS 
                             if indicator in text_lower)
        if confusion_score >= 2:
            alerts.append({
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': 'Customer appears to need assistance',
                'context': 'Confused behavior detected'
            })
        
        # Check for assistance needed
        assistance_score = sum(1 for indicator in AlertRules.ASSISTANCE_NEEDED_INDICATORS 
                              if indicator in text_lower)
        if assistance_score >= 2:
            alerts.append({
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': 'Customer may need product assistance',
                'context': 'High engagement with products'
            })
        
        # Check for high-value customer
        high_value_score = sum(1 for indicator in AlertRules.HIGH_VALUE_INDICATORS 
                              if indicator in text_lower)
        if high_value_score >= 1:
            alerts.append({
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.BOTH,
                'reason': 'High-value customer opportunity',
                'context': 'Premium customer detected'
            })
        
        # Check for negative emotions
        negative_indicators = ["frustrated", "annoyed", "impatient", "dissatisfied", "angry"]
        if any(indicator in text_lower for indicator in negative_indicators):
            alerts.append({
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.MANAGER,
                'reason': 'Customer showing negative emotions',
                'context': 'Potential service recovery needed'
            })
        
        return alerts
    
    @staticmethod
    def should_alert_zone_transition(from_zone: str, to_zone: str, frequency: int) -> Optional[Dict[str, Any]]:
        """Check if unusual zone transition patterns should trigger alert"""
        # Alert if customer repeatedly moves between same zones (possible confusion)
        if frequency >= 3:
            return {
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.OPERATIONS,
                'recipient': AlertRecipient.MANAGER,
                'reason': f'Unusual movement pattern: {frequency} transitions between {from_zone} and {to_zone}',
                'context': 'Possible navigation issue or obstruction'
            }
        return None
    
    @staticmethod
    def should_alert_system_issue(error_type: str, details: str) -> Dict[str, Any]:
        """Alert for system issues"""
        return {
            'priority': AlertPriority.HIGH,
            'category': AlertCategory.SYSTEM,
            'recipient': AlertRecipient.MANAGER,
            'reason': f'System issue: {error_type}',
            'context': details
        }

    @staticmethod
    def should_alert_person_entry(zone_type: str, is_premium_zone: bool = False) -> Optional[Dict[str, Any]]:
        """Alert when person enters important zones"""
        if is_premium_zone or zone_type in ['premium', 'high_value', 'jewelry', 'electronics']:
            return {
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': 'Customer entered premium area',
                'salesperson_priority': True
            }
        return None

    @staticmethod
    def should_alert_multiple_visits(visit_count: int, zone_name: str) -> Optional[Dict[str, Any]]:
        """Alert when customer returns to same zone multiple times"""
        if visit_count >= 3:
            return {
                'priority': AlertPriority.HIGH,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': f'Customer returned to {zone_name} {visit_count} times',
                'context': 'Strong purchase intent detected',
                'salesperson_priority': True
            }
        elif visit_count >= 2:
            return {
                'priority': AlertPriority.MEDIUM,
                'category': AlertCategory.CUSTOMER_SERVICE,
                'recipient': AlertRecipient.SALESPERSON,
                'reason': f'Customer returned to {zone_name}',
                'context': 'Repeat interest detected',
                'salesperson_priority': True
            }
        return None
