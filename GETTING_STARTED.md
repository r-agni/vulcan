# 🚀 Getting Started - Video AI Retail Analytics

## Step-by-Step Guide

### ✅ Step 1: Install Dependencies (5 minutes)

```bash
# Navigate to project directory
cd c:\Users\agni_\Documents\videoAI

# Install all requirements
pip install -r requirements.txt
```

**What gets installed:**
- FastAPI (web framework)
- OpenCV (computer vision)
- face-recognition (face detection)
- Google Gemini AI client
- yt-dlp & pafy (YouTube support)
- And more... (17 packages total)

---

### ✅ Step 2: Quick Test (1-2 minutes)

Run the YouTube video test to verify everything works:

```bash
python scripts\test_youtube.py
```

**What it does:**
- Loads YouTube retail store video
- Detects faces in real-time
- Adds persons to database
- Shows processed video window
- Runs for 60 seconds
- Prints results

**Expected Output:**
```
🎬 Starting YouTube Video Test...
================================================
1. ✓ Database initialized
2. ✓ Face detector ready
3. ✓ YouTube video loaded
4. Processing video...
------------------------------------------------
   [NEW] Person Person_20251018_132230 detected (ID: 1)
   Processed 600 frames in 60.0s
================================================
TEST RESULTS
================================================
Frames processed:    600
Total faces detected: XX
Unique persons:      X
Duration:            60.0s
================================================
✅ TEST PASSED
```

**If you see errors:**
- **YouTube loading fails:** Install `yt-dlp` manually: `pip install yt-dlp --upgrade`
- **Face detection fails:** Install CMake: `choco install cmake` (Windows)
- **Import errors:** Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

---

### ✅ Step 3: Run Full System (30 seconds)

Start the complete retail analytics server:

```bash
python app\main_retail.py
```

**What happens:**
- Database initialization with default zones/lines
- YouTube video loading
- Camera capture starts
- WebSocket server starts
- Dashboard becomes available

**Console output:**
```
Database initialized
Default zones created
Default virtual lines created
Loaded 5 active zones
Loaded 4 active virtual lines
✓ Face detector ready
YouTube video loaded successfully
Retail Analytics System started successfully!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### ✅ Step 4: Access Dashboard

Open your browser and navigate to:

```
http://localhost:8000
```

**What you'll see:**

**Live Video Feed** (left side)
- Real-time YouTube video with overlays
- Toggle buttons to show/hide:
  - 📦 Bounding Boxes
  - 🔵 Trajectory Paths
  - 🟢 Zone Boundaries
  - 🔥 Heatmap
  - 📏 Virtual Lines

**Analytics Metrics** (center)
- Current occupancy
- Peak occupancy
- Average dwell time
- Active trajectories
- Zone-by-zone analytics
- Entry/exit statistics
- Queue detection

**AI Analysis** (right side)
- Live Gemini AI insights
- Shopping behavior analysis
- Purchase intent scoring
- Customer emotions
- Traffic heatmap visualization

---

## 📊 Understanding the Dashboard

### Top Bar
- **Store Name:** Store #001
- **LIVE Status:** Green = running
- **Current Time:** Real-time clock

### Video Section
```
┌─────────────────────────────┐
│  📦 Boxes | 🔵 Paths | etc  │ ← Toggle overlays
├─────────────────────────────┤
│                             │
│    LIVE VIDEO FEED          │
│    with Overlays            │
│                             │
└─────────────────────────────┘
```

### Metrics Cards
```
┌──────────────────┐
│ Store Metrics    │
│ Occupancy: 5     │
│ Peak: 12         │
│ Dwell: 8m 20s    │
└──────────────────┘

┌──────────────────┐
│ Zone Analytics   │
│ Electronics: 3   │
│ Checkout: 2      │
│ Entrance: 1      │
└──────────────────┘
```

---

## 🎮 Interactive Features

### Toggle Overlays
Click the buttons in the video section:
- **📦 Boxes** - Show/hide person bounding boxes
- **🔵 Paths** - Show/hide trajectory trails
- **🟢 Zones** - Show/hide zone boundaries
- **🔥 Heatmap** - Show/hide traffic heatmap
- **📏 Lines** - Show/hide entry/exit lines

### Real-time Updates
Everything updates automatically via WebSocket:
- New person detected → Appears instantly
- Zone occupancy changes → Updates immediately
- Queue forms → Alert shows up
- AI analysis completes → Streams to dashboard

---

## ⚙️ Configuration

### Change Video Source

Edit `.env` file:

```env
# Use webcam
CAMERA_SOURCE=0

# Use local video file
CAMERA_SOURCE=C:\Videos\store_footage.mp4

# Use YouTube video (current)
CAMERA_SOURCE=https://www.youtube.com/watch?v=-1bRhYjw1qE

# Use IP camera
CAMERA_SOURCE=rtsp://camera_ip/stream
```

### Adjust Performance

```env
# Frame rate (lower = faster, less accurate)
CAMERA_FPS=10

# Heatmap resolution (lower = faster)
HEATMAP_RESOLUTION=20

# Trajectory history (lower = faster)
TRAJECTORY_HISTORY_SECONDS=30
```

### Add Custom Zones

Edit `config\default_zones.json`:

```json
{
  "zones": [
    {
      "name": "My Custom Zone",
      "zone_type": "product",
      "polygon_points": [
        [0.1, 0.1],  // Top-left (10%, 10%)
        [0.3, 0.1],  // Top-right (30%, 10%)
        [0.3, 0.3],  // Bottom-right (30%, 30%)
        [0.1, 0.3]   // Bottom-left (10%, 30%)
      ],
      "color": "#FF5733",
      "max_capacity": 20
    }
  ]
}
```

**Coordinates are normalized (0.0 to 1.0):**
- `[0.0, 0.0]` = Top-left corner
- `[1.0, 1.0]` = Bottom-right corner
- `[0.5, 0.5]` = Center of screen

---

## 🛠️ Troubleshooting

### YouTube Video Won't Load

```bash
# Upgrade yt-dlp
pip install yt-dlp --upgrade

# Test manually
python
>>> import pafy
>>> video = pafy.new("https://www.youtube.com/watch?v=-1bRhYjw1qE")
>>> print(video.title)
```

### Face Detection Not Working

```bash
# Check face_recognition installation
python -c "import face_recognition; print('OK')"

# Reinstall if needed
pip uninstall face-recognition face-recognition-models
pip install face-recognition
```

### Dashboard Won't Load

1. Check server is running: Look for "Uvicorn running on..."
2. Try different browser
3. Check firewall isn't blocking port 8000
4. Try `http://127.0.0.1:8000` instead of `localhost`

### Database Errors

```bash
# Delete old database and restart
del data\database\video_ai.db
python app\main_retail.py
```

---

## 📝 Next Steps

Once everything is working:

1. **Customize Zones** - Edit `config\default_zones.json`
2. **Customize Lines** - Edit `config\default_lines.json`
3. **Use Real Camera** - Change `CAMERA_SOURCE=0` in `.env`
4. **Export Analytics** - Use API endpoints (coming soon)
5. **Add More Cameras** - Multi-camera support (future)

---

## 📚 Learn More

- **[README.md](README.md)** - Quick overview
- **[COMPLETE_SYSTEM_SUMMARY.md](docs/COMPLETE_SYSTEM_SUMMARY.md)** - Full system details
- **[RETAIL_ANALYTICS_README.md](docs/RETAIL_ANALYTICS_README.md)** - Comprehensive guide
- **API Documentation:** http://localhost:8000/docs (when running)

---

## 💡 Pro Tips

1. **Performance:** Lower `CAMERA_FPS` to 5-10 for smooth processing
2. **Testing:** Use YouTube videos before deploying to real cameras
3. **Zones:** Start with a few zones, add more as needed
4. **Heatmap:** Takes 5-10 minutes to show meaningful data
5. **Database:** Backup `data/database/video_ai.db` regularly

---

## ✅ Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] YouTube test passed (`python scripts\test_youtube.py`)
- [ ] System running (`python app\main_retail.py`)
- [ ] Dashboard accessible (`http://localhost:8000`)
- [ ] Video shows overlays
- [ ] Faces being detected
- [ ] Analytics updating
- [ ] AI analysis working

---

**🎉 Congratulations! Your retail analytics system is ready to use!**

---

*For issues or questions, check the documentation in the `docs/` folder.*
