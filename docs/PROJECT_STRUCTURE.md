# 📁 Video AI Retail Analytics - Project Structure

## Optimized Folder Organization

```
videoAI/
│
├── 📁 app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                      # Application entry point
│   │
│   ├── 📁 api/                      # API endpoints
│   │   ├── __init__.py
│   │   ├── analytics.py             # Analytics endpoints
│   │   ├── persons.py               # Person management endpoints
│   │   ├── zones.py                 # Zone management endpoints
│   │   └── websocket.py             # WebSocket handlers
│   │
│   ├── 📁 core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py                # Configuration management
│   │   ├── camera_manager.py        # Camera capture logic
│   │   ├── face_detector.py         # Face detection/recognition
│   │   └── overlay_renderer.py      # Video overlay system
│   │
│   ├── 📁 analytics/                # Analytics modules
│   │   ├── __init__.py
│   │   ├── trajectory.py            # Trajectory tracking
│   │   ├── dwell_time.py            # Dwell time calculation
│   │   ├── occupancy.py             # Occupancy counting
│   │   ├── heatmap.py               # Heatmap generation
│   │   ├── line_crossing.py         # Line crossing detection
│   │   ├── queue_detector.py        # Queue detection
│   │   └── zone_detector.py         # Zone detection
│   │
│   ├── 📁 ai/                       # AI/ML modules
│   │   ├── __init__.py
│   │   ├── gemini_client.py         # Gemini API client
│   │   ├── prompts.py               # AI prompts library
│   │   └── analyzers.py             # Analysis functions
│   │
│   ├── 📁 db/                       # Database
│   │   ├── __init__.py
│   │   ├── base.py                  # Database connection
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic schemas
│   │   └── crud.py                  # CRUD operations
│   │
│   └── 📁 utils/                    # Utility functions
│       ├── __init__.py
│       ├── geometry.py              # Geometric calculations
│       ├── image_processing.py      # Image utilities
│       └── time_utils.py            # Time/date utilities
│
├── 📁 static/                       # Frontend assets
│   ├── 📁 css/
│   │   ├── retail_dashboard.css
│   │   └── common.css
│   ├── 📁 js/
│   │   ├── retail_dashboard.js
│   │   ├── analytics.js
│   │   └── websocket.js
│   ├── 📁 images/
│   │   └── logo.png
│   └── 📁 html/
│       ├── retail_dashboard.html
│       └── index.html
│
├── 📁 data/                         # Data storage
│   ├── 📁 database/
│   │   └── video_ai.db              # SQLite database
│   ├── 📁 uploads/
│   │   ├── frames/                  # Captured frames
│   │   ├── thumbnails/              # Person thumbnails
│   │   └── videos/                  # Recorded clips
│   ├── 📁 heatmaps/
│   │   └── hourly/                  # Generated heatmaps
│   └── 📁 exports/
│       ├── reports/                 # PDF/CSV reports
│       └── analytics/               # Exported analytics data
│
├── 📁 config/                       # Configuration files
│   ├── default_zones.json           # Default zone definitions
│   ├── default_lines.json           # Default virtual lines
│   └── settings.yaml                # App settings
│
├── 📁 scripts/                      # Utility scripts
│   ├── init_db.py                   # Database initialization
│   ├── seed_zones.py                # Seed default zones
│   ├── export_analytics.py          # Export analytics data
│   └── cleanup_old_data.py          # Data cleanup script
│
├── 📁 tests/                        # Unit tests
│   ├── __init__.py
│   ├── test_analytics.py
│   ├── test_face_detector.py
│   ├── test_zones.py
│   └── test_api.py
│
├── 📁 docs/                         # Documentation
│   ├── API.md                       # API documentation
│   ├── SETUP.md                     # Setup guide
│   ├── ANALYTICS_GUIDE.md           # Analytics guide
│   └── DEPLOYMENT.md                # Deployment guide
│
├── .env                             # Environment variables
├── .env.example                     # Example env file
├── .gitignore                       # Git ignore rules
├── requirements.txt                 # Python dependencies
├── requirements-dev.txt             # Development dependencies
├── README.md                        # Main README
├── RETAIL_ANALYTICS_README.md       # Retail analytics README
└── docker-compose.yml               # Docker composition (optional)

```

## Benefits of This Structure

### 1. **Separation of Concerns**
- `/app/api` - All API routes isolated
- `/app/core` - Core business logic
- `/app/analytics` - Analytics modules
- `/app/ai` - AI/ML functionality
- `/app/db` - Database layer

### 2. **Scalability**
- Easy to add new analytics modules
- Simple to add new API endpoints
- Modular architecture for team collaboration

### 3. **Maintainability**
- Clear module boundaries
- Easy to locate specific functionality
- Simplified testing

### 4. **Data Organization**
- All persistent data in `/data`
- Clean separation from code
- Easy backup and migration

### 5. **Professional Standards**
- Follows FastAPI best practices
- Aligns with Python packaging standards
- Docker-ready structure

---

## Migration Steps

1. Create new folder structure
2. Move existing files to appropriate locations
3. Update import paths
4. Update configuration
5. Test all functionality
6. Update documentation

---

## Import Path Examples

### Before (Flat Structure)
```python
from camera_manager import CameraManager
from face_detector import FaceDetector
from retail_analytics import TrajectoryTracker
```

### After (Organized Structure)
```python
from app.core.camera_manager import CameraManager
from app.core.face_detector import FaceDetector
from app.analytics.trajectory import TrajectoryTracker
```

---

## Database Location

**Before:** `./video_ai.db` (root directory)

**After:** `./data/database/video_ai.db`

Update in `.env`:
```env
DATABASE_URL=sqlite:///./data/database/video_ai.db
```

---

## Static Files Serving

Update FastAPI static mounts:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")
```

---

This structure is production-ready and follows industry best practices!
