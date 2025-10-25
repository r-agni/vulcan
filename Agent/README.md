# Agent - Intelligent Alert System

Gemini-powered real-time alert generation for retail surveillance.

## Overview

The Agent system continuously monitors retail analytics data and generates intelligent, contextual alerts for salespersons and managers using Google's Gemini AI.

## Architecture

```
Agent/
├── __init__.py              # Package initialization
├── alert_types.py           # Alert data structures and enums
├── alert_rules.py           # Business rules for alert triggers
├── alert_generator.py       # Gemini AI alert generation
├── alert_manager.py         # Alert queue and lifecycle management
└── README.md               # This file
```

## Components

### 1. Alert Types (`alert_types.py`)

Defines core alert structures:
- **AlertPriority**: LOW, MEDIUM, HIGH, CRITICAL
- **AlertCategory**: CUSTOMER_SERVICE, QUEUE_MANAGEMENT, SECURITY, OPERATIONS, CAPACITY, SYSTEM
- **AlertRecipient**: SALESPERSON, MANAGER, BOTH
- **Alert**: Main data class with full alert details

### 2. Alert Rules (`alert_rules.py`)

Business logic for alert triggers:
- **Dwell Time Thresholds**: 5min (assistance), 10min (extended), 15min (unusual)
- **Queue Thresholds**: 5 customers (warning), 7+ (critical)
- **Occupancy Thresholds**: 75% (warning), 90% (critical)
- **Behavior Analysis**: Detects confusion, assistance needs, high-value customers

### 3. Alert Generator (`alert_generator.py`)

Gemini-powered intelligent alert generation:
- **Rule-Based Alerts**: Fast, deterministic alerts from predefined rules
- **Behavior Analysis Alerts**: Pattern recognition from Gemini analysis
- **AI-Generated Alerts**: Context-aware alerts from real-time data
- **Summary Alerts**: Periodic overview for management

### 4. Alert Manager (`alert_manager.py`)

Queue management and delivery:
- **Deduplication**: Prevents spam alerts
- **Priority Queue**: Highest priority alerts displayed first
- **Auto-Expiry**: Alerts expire after 10 minutes
- **Acknowledgment**: Track alert resolution
- **History**: Maintains alert log

## Alert Examples

### Salesperson Alerts

```
🛎️ Customer in Electronics zone
Customer may need assistance: 5 minutes in zone
Priority: MEDIUM | For: Sales Staff
```

```
🛎️ High-value customer opportunity
Premium customer detected
Priority: HIGH | For: Sales Staff
```

### Manager Alerts

```
⏱️ Queue Alert: Checkout
Critical queue length: 7 customers waiting
Priority: CRITICAL | For: Manager
```

```
👥 Capacity Alert: Store
Near capacity: 45/50 (90%)
Priority: CRITICAL | For: Manager
```

## Integration

### Backend (`app/main.py`)

```python
from Agent import AlertGenerator, AlertManager

# Initialize
alert_generator = AlertGenerator(api_key=os.getenv("GEMINI_API_KEY"))
alert_manager = AlertManager(max_queue_size=50, alert_expiry_seconds=600)

# Generate alerts
alerts = alert_generator.analyze_and_generate_alerts(
    analytics_data=analytics_data,
    behavior_analysis=behavior_text,
    timestamp_data=timestamp_data
)

# Add to queue
added_alerts = alert_manager.add_alerts(alerts)
```

### Frontend (`static/dashboard.js`)

```javascript
// WebSocket connection
alertsWS = new WebSocket(`${WS_PROTOCOL}//${WS_HOST}/ws/alerts`);

// Receive alerts
alertsWS.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'alerts') {
        updateAlerts(data.data);
    }
};

// Dismiss alert
async function dismissAlert(alertId) {
    await fetch(`/api/alerts/${alertId}/dismiss`, { method: 'POST' });
}
```

## API Endpoints

- `GET /api/alerts` - Get active alerts (optional recipient filter)
- `POST /api/alerts/{alert_id}/acknowledge` - Acknowledge alert
- `POST /api/alerts/{alert_id}/dismiss` - Dismiss alert
- `GET /api/alerts/statistics` - Get alert statistics
- `WS /ws/alerts` - Real-time alert stream

## Configuration

Alert thresholds can be adjusted in `alert_rules.py`:

```python
# Dwell time thresholds (seconds)
DWELL_TIME_ASSISTANCE_THRESHOLD = 300  # 5 minutes
DWELL_TIME_EXTENDED_THRESHOLD = 600    # 10 minutes
DWELL_TIME_UNUSUAL_THRESHOLD = 900     # 15 minutes

# Queue thresholds
QUEUE_LENGTH_WARNING = 5
QUEUE_LENGTH_CRITICAL = 7

# Occupancy thresholds (percent)
OCCUPANCY_WARNING_PERCENT = 0.75  # 75%
OCCUPANCY_CRITICAL_PERCENT = 0.90  # 90%
```

## Alert Lifecycle

1. **Generation**: Analytics data triggers rule-based or AI-generated alerts
2. **Validation**: Deduplication prevents spam
3. **Queue**: Added to priority queue
4. **Display**: Broadcast via WebSocket to dashboard
5. **Action**: Staff acknowledges or dismisses
6. **Expiry**: Auto-expires after 10 minutes
7. **History**: Logged to database for analysis

## Dashboard Display

Alerts appear in a banner below the header:
- Color-coded by priority (blue=low, orange=medium, red=high, dark red=critical)
- Category icons (🛎️ service, ⏱️ queue, 🔒 security, ⚙️ operations, 👥 capacity)
- Recipient badges (Sales, Manager, All Staff)
- Dismiss button for quick removal
- Max 5 alerts shown at once
- Auto-scroll for new alerts

## Future Enhancements

- **SMS/Email Notifications**: Send critical alerts via external channels
- **Alert Routing**: Route alerts to specific staff based on zone/role
- **Machine Learning**: Learn from alert patterns to improve accuracy
- **Custom Rules**: User-configurable alert rules per store
- **Analytics Dashboard**: Alert frequency, response times, effectiveness metrics
- **Integration**: POS systems, inventory management, scheduling software

## Dependencies

- `google-genai`: Gemini AI API
- `fastapi`: WebSocket support
- `sqlalchemy`: Alert logging to database

## License

Part of the Video AI Surveillance System
