# 🏬 Retail Store Analytics AI System

## Complete Video AI Solution for Retail Analytics

An advanced, end-to-end retail analytics platform powered by computer vision and Google Gemini AI. Track customers, analyze behavior, optimize store layout, and gain actionable insights from your camera feeds.

---

## 🎯 Features

### Core Analytics

#### 1. **Queue Analytics** 📋
- Automatic queue/line detection
- Real-time queue length monitoring
- Average wait time calculation
- Queue abandonment risk detection
- Alerts for long queues (>5 people)

#### 2. **Shopper Occupancy** 👥
- Real-time people counting across entire store
- Zone-based occupancy tracking
- Peak hour identification
- Capacity threshold monitoring with alerts
- Historical occupancy trends

#### 3. **Dwell Time Analysis** ⏱️
- Time spent per zone calculation
- Product engagement scoring (0-1 scale)
- Average session duration tracking
- Zone entry/exit logging
- Attention heatmaps

#### 4. **Trajectory Tracking** 🚶
- 30-second path visualization
- Entry-to-exit journey mapping
- Common pathway identification
- Navigation efficiency analysis
- Multi-person tracking (color-coded)

#### 5. **Heat Mapping** 🗺️
- Traffic density visualization
- Hot zone identification
- Cold zone detection
- Hourly/daily aggregation
- Semi-transparent overlay on video feed

#### 6. **Proximity Analytics** 📍
- Product interaction detection
- Engagement distance measurement
- Proximity circles (0-200cm ranges)
- Product pick-up/put-back tracking

#### 7. **Line Crossing** 🚧
- Virtual boundary definitions
- Entry/exit counting
- Directional flow tracking (in/out)
- Real-time crossing visualizations
- Per-line statistics

#### 8. **Regions of Interest (ROI)** 🎯
- Custom zone creation (polygon-based)
- Per-zone analytics
- Zone transition tracking
- Capacity limits per zone
- Color-coded zone visualization

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RETAIL ANALYTICS DASHBOARD                    │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Live Video Feed  │  │  Analytics   │  │  AI Analysis      │  │
│  │  with Overlays   │  │   Widgets    │  │  & Heatmaps       │  │
│  └──────────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↑ WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS ENGINE (FastAPI)                    │
│  ┌────────────────┬───────────────┬──────────────────────────┐  │
│  │ CV Analytics   │ Gemini AI     │ Real-time Aggregation    │  │
│  │ • Trajectory   │ • Shopping    │ • Occupancy logging      │  │
│  │ • Dwell Time   │ • Queue exp   │ • Heatmap generation     │  │
│  │ • Occupancy    │ • Layout opt  │ • Alert generation       │  │
│  │ • Line Cross   │ • Product int │ • Metrics calculation    │  │
│  └────────────────┴───────────────┴──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↑ ↑ ↑
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (SQLite / PostgreSQL)                │
│  Persons │ Zones │ Trajectories │ Dwell Records │ Heatmaps      │
│  Events  │ Lines │ Occupancy    │ Queues        │ Interactions  │
└─────────────────────────────────────────────────────────────────┘
                               ↑ ↑ ↑
┌─────────────────────────────────────────────────────────────────┐
│                      VIDEO CAPTURE (OpenCV)                      │
│              Camera Feed @ 1280x720 30fps                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Video Overlay Visualization

The system renders real-time analytics overlays directly on the video feed:

### Overlay Layers (Togglable)

1. **Bounding Boxes** (Green/Orange)
   - Person name label
   - Current dwell time
   - Zone indicator

2. **Trajectory Paths** (Multi-color)
   - Fading trail (last 30 seconds)
   - Start point (filled circle)
   - Current position (pulsing circle)
   - 6 distinct colors for tracking

3. **Zone Boundaries** (Color-coded polygons)
   - Semi-transparent fill (15% opacity)
   - Solid border
   - Zone name label at centroid
   - Current occupancy count

4. **Virtual Lines** (Red/Custom color)
   - Solid line boundary
   - In/Out count labels
   - Animated crossing indicators

5. **Heatmap Overlay** (COLORMAP_JET)
   - 50% transparency
   - Blue (low) → Green → Yellow → Red (high)
   - Gaussian-blurred for smoothness

6. **Queue Visualization**
   - Numbered circles (queue position)
   - Queue length badge
   - Orange highlight

7. **Proximity Circles** (Animated rings)
   - Green: 0-50cm (touching)
   - Yellow: 50-100cm (examining)
   - Blue: 100-200cm (nearby)

8. **Alert Badges** (Top-right overlay)
   - Queue alerts (orange)
   - Capacity warnings (red)
   - Auto-dismiss after resolution

---

## 🗄️ Database Schema

### New Tables (9 total)

```sql
-- Zone definitions
zones
├── id (PK)
├── name (VARCHAR)
├── zone_type (VARCHAR) -- product, queue, entrance, aisle
├── polygon_points (JSON) -- [[x,y], [x,y], ...]
├── color (VARCHAR) -- #RRGGBB
├── max_capacity (INT)
└── is_active (BOOLEAN)

-- Person movement tracking
person_trajectories
├── id (PK)
├── person_id (FK → persons)
├── session_id (UUID)
├── timestamp (DATETIME)
├── x_position (FLOAT 0-1)
├── y_position (FLOAT 0-1)
└── zone_id (FK → zones)

-- Dwell time records
dwell_time_records
├── id (PK)
├── person_id (FK → persons)
├── session_id (UUID)
├── zone_id (FK → zones)
├── entry_time (DATETIME)
├── exit_time (DATETIME)
├── duration_seconds (INT)
└── engagement_score (FLOAT 0-1)

-- Virtual counting lines
virtual_lines
├── id (PK)
├── name (VARCHAR)
├── start_point (JSON) -- {x, y}
├── end_point (JSON) -- {x, y}
├── count_direction (VARCHAR) -- in, out, both
└── color (VARCHAR)

-- Line crossing events
line_crossing_events
├── id (PK)
├── person_id (FK → persons)
├── line_id (FK → virtual_lines)
├── timestamp (DATETIME)
├── direction (VARCHAR) -- in, out
└── crossing_point (JSON)

-- Occupancy tracking
occupancy_logs
├── id (PK)
├── timestamp (DATETIME)
├── zone_id (FK → zones) -- NULL = entire store
├── person_count (INT)
└── person_ids (JSON)

-- Queue metrics
queue_metrics
├── id (PK)
├── zone_id (FK → zones)
├── timestamp (DATETIME)
├── queue_length (INT)
├── avg_wait_time_seconds (FLOAT)
├── max_wait_time_seconds (FLOAT)
└── people_in_queue (JSON)

-- Heatmap data
heatmap_data
├── id (PK)
├── timestamp (DATETIME)
├── time_bucket (VARCHAR) -- YYYY-MM-DD_HH:00
├── heatmap_array (BLOB) -- serialized numpy
├── max_intensity (FLOAT)
└── image_path (VARCHAR)

-- Product interactions
product_interactions
├── id (PK)
├── person_id (FK → persons)
├── zone_id (FK → zones)
├── timestamp (DATETIME)
├── interaction_type (VARCHAR) -- looked_at, picked_up, examined
├── duration_seconds (FLOAT)
├── proximity_cm (FLOAT)
└── engagement_score (FLOAT 0-1)
```

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run retail analytics system
python main_retail.py
```

### Access Dashboard

```
http://localhost:8000
```

The system will:
1. Initialize database with default zones
2. Create 4 sample zones: Entrance, Checkout, Electronics, Clothing
3. Create 2 virtual lines: Store Entrance, Checkout Line
4. Start camera capture
5. Begin real-time analytics

---

## 🎨 Dashboard Features

### Live Video Feed
- Real-time camera stream with overlays
- Toggle overlay layers individually
- Full HD video (1280x720)

### Analytics Widgets

#### Store Metrics
- Current occupancy (real-time)
- Peak occupancy (daily)
- Average dwell time
- Active trajectories count

#### Zone Analytics
- Per-zone occupancy
- Color-coded zones
- Capacity indicators

#### Entry/Exit Tracking
- Per-line in/out counts
- Cumulative statistics
- Directional flow

#### Queue Analytics
- Active queue detection
- Queue length display
- Wait time estimates

#### Alerts
- Auto-alerts for queues >5 people
- Capacity warnings (>80% full)
- Real-time notifications

### AI Analysis Panel
- Live Gemini analysis streaming
- Context-aware prompts based on zone type
- Shopping behavior insights
- Purchase intent scoring
- Queue experience analysis
- Layout optimization recommendations

### Traffic Heatmap
- Visual heat distribution
- Color-gradient legend
- Updates every 5 minutes

---

## 🤖 Gemini AI Integration

### Retail-Specific Analysis

#### 1. Shopping Behavior Analysis
```python
gemini_analyzer.analyze_shopping_behavior(video_path)
```

**Analyzes:**
- Product displays examined
- Time spent per location (with timestamps)
- Pick-up/put-back behavior
- Price checking indicators
- Purposeful vs. browsing patterns
- Purchase intent (0-10 rating)
- Emotional satisfaction levels

#### 2. Queue Experience Analysis
```python
gemini_analyzer.analyze_queue_experience(video_path)
```

**Analyzes:**
- Customer patience levels
- Body language (fidgeting, time-checking)
- Queue abandonment risk (1-10)
- Engagement while waiting
- Staff responsiveness
- Improvement suggestions

#### 3. Store Layout Effectiveness
```python
gemini_analyzer.analyze_store_layout_effectiveness(video_path)
```

**Analyzes:**
- Navigation efficiency (1-10 rating)
- Confusion points and dead-ends
- Congestion/bottleneck areas
- Display effectiveness
- Signage adequacy
- Optimization recommendations

#### 4. Product Interaction Analysis
```python
gemini_analyzer.analyze_product_interaction(video_path, zone_name)
```

**Analyzes:**
- Engagement level (casual vs. deep)
- Time examining products
- Comparison behaviors
- Purchase likelihood (1-10)
- Display effectiveness
- Conversion optimization tips

---

## 🔧 Zone Management API

### Create Zone

```bash
POST /api/zones/
{
  "name": "Electronics",
  "zone_type": "product",
  "polygon_points": [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]],
  "color": "#0000FF",
  "max_capacity": 30
}
```

### Create Virtual Line

```bash
POST /api/zones/lines
{
  "name": "Store Entrance",
  "start_point": {"x": 0.0, "y": 0.2},
  "end_point": {"x": 0.3, "y": 0.2},
  "count_direction": "both",
  "color": "#FF0000"
}
```

### Get All Zones

```bash
GET /api/zones/
```

### Get Zone Analytics

```bash
GET /api/analytics/current
```

---

## 📈 Use Cases

### 1. Store Layout Optimization
- Identify high-traffic areas for premium product placement
- Detect dead zones for layout improvements
- Optimize customer flow with pathway analysis

### 2. Staffing Optimization
- Queue analytics for checkout staffing decisions
- Peak hour identification for shift planning
- Real-time alerts for immediate assistance

### 3. Customer Experience Enhancement
- Reduce queue wait times
- Improve product findability
- Optimize store navigation

### 4. Sales Conversion Improvement
- Analyze product interaction patterns
- Identify high-engagement displays
- Measure purchase intent signals

### 5. Security & Safety
- Occupancy compliance monitoring
- Emergency evacuation planning
- Suspicious behavior detection

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./video_ai.db
CAMERA_SOURCE=0
FPS_SAMPLING=1
```

### Camera Sources

```python
CAMERA_SOURCE=0           # Default webcam
CAMERA_SOURCE=1           # Second camera
CAMERA_SOURCE="rtsp://..." # IP camera RTSP stream
CAMERA_SOURCE="video.mp4"  # Video file (testing)
```

### Performance Tuning

```python
# Frame processing rate (lower = better performance)
camera = CameraManager(fps=15)  # Default: 30

# Trajectory history duration
trajectory_tracker = TrajectoryTracker(history_duration_seconds=20)  # Default: 30

# Heatmap resolution (higher = better detail, slower)
heatmap_generator = HeatmapGenerator(resolution=20)  # Default: 20

# Occupancy logging interval (seconds)
# In main_retail.py, line 212
if (timestamp - last_occupancy_log_time).total_seconds() > 300:  # 5 minutes
```

---

## 🎯 Best Practices

### Zone Setup
1. **Define clear boundaries** - Use store layout diagrams
2. **Avoid overlapping zones** - Each area should have one primary zone
3. **Set realistic capacities** - Based on fire code and comfort
4. **Use descriptive names** - "Electronics Section" not "Zone 1"

### Virtual Lines
1. **Place at entry/exit points** - Perpendicular to customer flow
2. **Count both directions** - For net traffic calculation
3. **Multiple checkout lines** - One virtual line per register

### Heatmap Interpretation
- **Red zones** - High traffic, popular areas
- **Blue zones** - Low traffic, consider relocation or removal
- **Green/Yellow** - Normal traffic

### Analytics Review Schedule
- **Real-time** - Queue alerts, capacity warnings
- **Hourly** - Occupancy trends, zone analytics
- **Daily** - Heatmaps, trajectory patterns
- **Weekly** - Layout optimization, conversion analysis

---

## 🔒 Privacy & Security

### Data Protection
- Face encodings stored as encrypted binary
- Video clips auto-deleted after 30 days
- No personally identifiable information stored
- GDPR/CCPA compliant design

### Compliance
- Post visible signage about video surveillance
- Obtain legal counsel for biometric data laws
- Implement data retention policies
- Regular security audits

---

## 🐛 Troubleshooting

### No overlays showing
- Check overlay toggle buttons are active
- Verify zones/lines configured in database
- Inspect browser console for errors

### Low frame rate
- Reduce camera FPS: `camera = CameraManager(fps=15)`
- Disable heatmap overlay
- Lower video resolution
- Use dedicated GPU if available

### Inaccurate occupancy
- Calibrate zone boundaries
- Adjust face detection tolerance
- Check camera angle and lighting
- Verify zone detector loaded zones

### Gemini API errors
- Check API key in .env
- Verify quota limits
- Ensure video files <20MB for inline
- Check network connectivity

---

## 📚 File Structure

```
videoAI/
├── main_retail.py              # Main retail analytics application
├── retail_analytics.py         # CV analytics modules
├── video_overlay.py            # Overlay rendering system
├── zone_manager.py             # Zone management API
├── gemini_analyzer.py          # Gemini AI integration (enhanced)
├── database.py                 # Extended database models
├── camera_manager.py           # Camera capture
├── face_detector.py            # Face detection/recognition
├── static/
│   ├── retail_dashboard.html   # Retail dashboard UI
│   ├── retail_styles.css       # Dashboard styling
│   └── retail_dashboard.js     # Dashboard JavaScript
├── requirements.txt            # Python dependencies
└── RETAIL_ANALYTICS_README.md  # This file
```

---

## 🚀 Future Enhancements

- [ ] Multi-camera support with camera switching
- [ ] Export analytics reports (PDF/Excel)
- [ ] Email/SMS alerts for critical events
- [ ] Integration with POS systems
- [ ] Predictive analytics with ML models
- [ ] Mobile app for remote monitoring
- [ ] Customer demographics analysis
- [ ] A/B testing for display effectiveness
- [ ] Integration with inventory management
- [ ] Staff performance tracking

---

## 📞 Support

For issues, questions, or feature requests:
- GitHub Issues: [Create Issue](#)
- Documentation: [docs.claude.com](https://docs.claude.com)
- Gemini API: [ai.google.dev](https://ai.google.dev)

---

## 📄 License

This project is for educational and commercial use. Ensure compliance with local privacy and surveillance laws.

---

## 🙏 Credits

- **Face Recognition**: [face_recognition](https://github.com/ageitgey/face_recognition)
- **AI Analysis**: Google Gemini 2.5 Flash
- **Web Framework**: FastAPI
- **Computer Vision**: OpenCV
- **Analytics**: Custom CV algorithms

---

**Built with ❤️ for retail innovation**
