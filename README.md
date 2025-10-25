# 🏬 Video AI Retail Analytics

> AI-powered retail analytics system with real-time face detection, behavior analysis, and comprehensive store metrics.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test with YouTube Video
```bash
python scripts/test_youtube.py
```

### 3. Run Full System
```bash
python app/main_retail.py
```

### 4. Open Dashboard
```
http://localhost:8000
```

---

## ✨ Features

- **8 Retail Analytics** - Queue, Occupancy, Dwell Time, Trajectory, Heatmap, Proximity, Line Crossing, ROI
- **AI-Powered Insights** - Google Gemini 2.5 Flash for behavior analysis
- **Real-time Dashboard** - Live video feed with 8 overlay layers
- **YouTube Support** - Test with any YouTube video
- **Face Recognition** - Automatic person detection and tracking
- **Zone Management** - Custom polygonal zones with analytics

---

## 📁 Project Structure

```
videoAI/
├── app/                    # Application code
│   ├── main_retail.py     # Main application (START HERE)
│   ├── database.py        # Database models (12 tables)
│   ├── camera_manager.py  # Video capture
│   ├── face_detector.py   # Face detection
│   ├── retail_analytics.py # Analytics modules
│   ├── video_overlay.py   # Overlay rendering
│   ├── zone_manager.py    # Zone management API
│   └── gemini_analyzer.py # AI analysis
│
├── config/                # Configuration files
│   ├── default_zones.json # Pre-configured zones
│   └── default_lines.json # Pre-configured lines
│
├── data/                  # Data storage (auto-created)
│   ├── database/          # SQLite database
│   ├── uploads/           # Frames, videos, thumbnails
│   └── heatmaps/          # Generated heatmaps
│
├── static/                # Frontend assets
│   ├── html/              # Dashboard HTML
│   ├── css/               # Stylesheets
│   └── js/                # JavaScript
│
├── scripts/               # Utility scripts
│   └── test_youtube.py    # YouTube test script
│
├── docs/                  # Documentation
│   ├── README.md          # This file (moved)
│   ├── RETAIL_ANALYTICS_README.md  # Full guide
│   └── COMPLETE_SYSTEM_SUMMARY.md  # System summary
│
├── .env                   # Environment configuration
├── .env.example           # Example configuration
└── requirements.txt       # Python dependencies
```

---

## 🎯 Current Configuration

The system is **pre-configured** to test with a YouTube retail store video:

```env
CAMERA_SOURCE=https://www.youtube.com/watch?v=-1bRhYjw1qE
GEMINI_API_KEY=AIzaSyC1yUWBHlqoUW-H1EDi9j62DZpkk6otoeY
DATABASE_URL=sqlite:///./data/database/video_ai.db
```

**To use your own camera:** Change `CAMERA_SOURCE=0` in `.env`

---

## 📊 Analytics Features

### Real-time Metrics
- Store occupancy (current & peak)
- Zone-based people counting
- Average dwell time
- Active trajectory tracking

### Video Overlays (Toggleable)
- ✅ Bounding boxes with person info
- ✅ Trajectory paths (30-second trails)
- ✅ Zone boundaries with occupancy
- ✅ Virtual lines for entry/exit counting
- ✅ Traffic heatmap
- ✅ Queue visualization
- ✅ Proximity circles
- ✅ Alert badges

### AI Analysis (Gemini)
- Shopping behavior & purchase intent
- Queue experience & wait perception
- Store layout effectiveness
- Product interaction analysis

---

## 🛠️ Key Technologies

- **FastAPI** - Modern Python web framework
- **OpenCV** - Computer vision
- **DeepFace** - Face detection/recognition (Windows-compatible, no dlib dependency)
- **Google Gemini 2.5** - AI analysis
- **SQLAlchemy** - Database ORM
- **WebSocket** - Real-time updates
- **yt-dlp** - YouTube video support

---

## 📖 Documentation

- **[Complete System Summary](docs/COMPLETE_SYSTEM_SUMMARY.md)** - Full feature overview
- **[Retail Analytics Guide](docs/RETAIL_ANALYTICS_README.md)** - Comprehensive 400+ line guide
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Architecture details

---

## 🔧 Configuration

### Change Video Source
Edit `.env`:
```env
CAMERA_SOURCE=0  # Webcam
CAMERA_SOURCE=/path/to/video.mp4  # Video file
CAMERA_SOURCE=https://youtube.com/...  # YouTube URL
```

### Adjust Performance
```env
CAMERA_FPS=10  # Lower = better performance
HEATMAP_RESOLUTION=20  # Lower = faster
```

### Add Custom Zones
Edit `config/default_zones.json` or use API:
```bash
POST /api/zones/
{
  "name": "New Zone",
  "zone_type": "product",
  "polygon_points": [[0.1, 0.2], [0.3, 0.4], ...],
  "color": "#FF0000",
  "max_capacity": 25
}
```

---

## 🧪 Testing

```bash
# Quick test (60 seconds)
python scripts/test_youtube.py

# Expected output:
# ✓ Database initialized
# ✓ Face detector ready
# ✓ YouTube video loaded
# Processed 600 frames in 60.0s
# Unique persons: X
```

---

## 📈 System Requirements

- **Python:** 3.8+
- **RAM:** 4GB minimum (8GB recommended)
- **CPU:** Multi-core processor
- **GPU:** Optional (for CNN face detection)
- **Disk:** 1GB+ for data storage

---

## ⚠️ Important Notes

- **Privacy:** Face encodings stored locally. Review privacy laws before deployment.
- **Performance:** YouTube video is set to 10 FPS for smooth processing.
- **Gemini API:** Limited free tier. Check quota at ai.google.dev.
- **Database:** Uses SQLite by default. Use PostgreSQL for production.

---

## 🎓 Use Cases

- Store layout optimization
- Queue management
- Staffing optimization
- Customer experience analysis
- Product placement effectiveness
- Traffic flow analysis
- Heat mapping
- Conversion rate optimization

---

## 🤝 Contributing

This is a complete, working system. To extend:

1. Add new analytics modules to `app/retail_analytics.py`
2. Create new API endpoints in `app/zone_manager.py`
3. Extend dashboard in `static/` folder
4. Add AI prompts in `app/gemini_analyzer.py`

---

## 📄 License

MIT License - Free for educational and commercial use.

**Important:** Ensure compliance with:
- Privacy laws (GDPR, CCPA)
- Biometric data regulations
- Video surveillance laws in your jurisdiction

---

## 🙏 Credits

- **DeepFace** - Sefik Ilkin Serengil (Windows-compatible facial recognition)
- **Google Gemini** - Advanced AI model
- **FastAPI** - Sebastián Ramírez
- **OpenCV** - Computer Vision community

---

## 📞 Support

- **Full Documentation:** See `docs/` folder
- **Test Script:** `python scripts/test_youtube.py`
- **API Docs:** http://localhost:8000/docs (when running)
- **Gemini Docs:** https://ai.google.dev
- **FastAPI Docs:** https://fastapi.tiangolo.com

---

**Built with ❤️ for retail innovation**

---

*Version 2.0.0 - Complete Retail Analytics System*
