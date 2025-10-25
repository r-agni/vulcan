# Video AI Surveillance System

An intelligent video surveillance system that uses AI for real-time face detection, person tracking, and behavioral analysis using Google's Gemini AI.

## Features

- **Real-time Face Detection**: Automatically detects and recognizes people using the camera feed
- **Person Database**: Maintains a local database of detected individuals with visit tracking
- **AI Behavior Analysis**: Uses Gemini 2.5 Flash to analyze:
  - Person appearance and clothing
  - Emotional state and body language
  - Movement patterns and pathways
  - Areas of interest and interactions
  - Timestamps for key events
- **Live Dashboard**: Web-based interface with:
  - Live video feed display
  - Real-time person profile sidebar
  - Streaming AI analysis
  - Person database viewer

## System Architecture

```
├── main.py                 # FastAPI backend server
├── database.py             # SQLAlchemy database models
├── camera_manager.py       # Camera capture and video recording
├── face_detector.py        # Face detection and recognition
├── gemini_analyzer.py      # Gemini AI video analysis
├── static/
│   ├── index.html         # Dashboard HTML
│   ├── styles.css         # Dashboard styling
│   └── app.js             # WebSocket and frontend logic
├── requirements.txt        # Python dependencies
└── .env                   # Configuration
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Webcam or IP camera
- Gemini API key (already configured in .env)

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Install System Dependencies

**For Windows:**
```bash
# CMake is required for face_recognition
# Download and install from: https://cmake.org/download/

# Or use chocolatey:
choco install cmake
```

**For Linux:**
```bash
sudo apt-get update
sudo apt-get install cmake build-essential
```

**For macOS:**
```bash
brew install cmake
```

### Step 3: Configure Environment

The `.env` file is already configured with:
- Gemini API key
- Camera source (0 for default webcam)
- Database settings

You can modify these settings if needed:

```env
GEMINI_API_KEY=AIzaSyC1yUWBHlqoUW-H1EDi9j62DZpkk6otoeY
DATABASE_URL=sqlite:///./video_ai.db
CAMERA_SOURCE=0
FPS_SAMPLING=1
```

### Step 4: Create Required Directories

The system will auto-create these, but you can create them manually:

```bash
mkdir uploads uploads/frames uploads/thumbnails temp_videos static
```

## Running the Application

### Start the Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8000
```

## How It Works

### 1. Face Detection Pipeline

1. Camera captures live video feed at 30 FPS
2. Each frame is processed for face detection using the `face_recognition` library
3. Detected faces are encoded into 128-dimensional vectors
4. Face encodings are compared against the database
5. Match found: Update person's visit record
6. No match: Create new person entry in database

### 2. Behavior Analysis Pipeline

When a person is detected:

1. System records a 10-second video clip
2. Clip is uploaded to Gemini API
3. AI analyzes the video for:
   - Physical appearance and clothing
   - Emotional state
   - Movement patterns
   - Areas of interest
   - Specific actions and behaviors
4. Analysis is saved to database
5. Results are streamed to dashboard in real-time

### 3. Dashboard Real-time Updates

- WebSocket connection maintains live communication
- Person detection triggers profile display in sidebar
- AI analysis streams to dashboard as it completes
- Person database refreshes automatically

## API Endpoints

### REST API

- `GET /` - Dashboard HTML
- `GET /video_feed` - Live video stream (MJPEG)
- `GET /api/persons` - Get all persons from database
- `GET /api/person/{person_id}` - Get person details with analyses
- `GET /api/current_detection` - Get currently detected person

### WebSocket

- `WS /ws` - WebSocket endpoint for real-time updates
  - Receives `detection` events when person detected
  - Receives `analysis` events when AI analysis completes

## Database Schema

### Person Table
- `id`: Primary key
- `name`: Person name (auto-generated or manual)
- `face_encoding`: Binary face encoding vector
- `first_seen`: First detection timestamp
- `last_seen`: Most recent detection timestamp
- `visit_count`: Number of times detected
- `thumbnail_path`: Path to face thumbnail
- `notes`: Optional notes

### DetectionEvent Table
- `id`: Primary key
- `person_id`: Foreign key to Person
- `timestamp`: Detection time
- `confidence`: Match confidence score
- `frame_path`: Path to captured frame
- `location`: Camera location identifier

### BehaviorAnalysis Table
- `id`: Primary key
- `person_id`: Foreign key to Person
- `detection_event_id`: Foreign key to DetectionEvent
- `timestamp`: Analysis time
- `analysis_type`: Type of analysis
- `analysis_text`: AI-generated analysis
- `video_clip_path`: Path to analyzed video clip

## Gemini AI Integration

### Video Analysis Capabilities

The system uses Gemini 2.5 Flash model with:

- **Video file upload**: For clips > 20MB or longer duration
- **Frame sampling**: Default 1 FPS, configurable up to 5 FPS
- **Multimodal analysis**: Processes both visual and audio
- **Timestamp references**: Can reference specific moments (MM:SS format)

### Analysis Types

1. **Full Behavior Analysis** (default)
   - Comprehensive person profiling
   - Movement pattern tracking
   - Interest area identification

2. **Single Frame Analysis**
   - Quick snapshot assessment
   - Clothing and appearance
   - Emotional state

3. **Custom FPS Analysis**
   - Detailed action tracking
   - Higher frame sampling (2-5 FPS)
   - Better for fast movements

4. **Clip Comparison**
   - Compare inside/outside camera footage
   - Track person across multiple cameras

## Customization

### Adjust Face Recognition Sensitivity

In `face_detector.py`:
```python
face_detector = FaceDetector(tolerance=0.6)  # Lower = stricter matching
```

### Change Video Recording Duration

In `main.py`:
```python
video_path = camera.record_clip(duration=10)  # Seconds
```

### Modify Analysis Prompt

In `gemini_analyzer.py`, customize the analysis prompt:
```python
prompt = """
Your custom analysis instructions here...
"""
```

### Use Different Camera Source

In `.env`:
```env
CAMERA_SOURCE=0           # Default webcam
CAMERA_SOURCE=1           # Second camera
CAMERA_SOURCE=rtsp://...  # IP camera RTSP stream
```

## Troubleshooting

### Camera Not Opening

```python
# Test camera access
import cv2
cap = cv2.VideoCapture(0)
print(cap.isOpened())  # Should be True
```

### Face Recognition Installation Issues

```bash
# For Windows, ensure Visual Studio C++ tools are installed
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Then reinstall face_recognition
pip uninstall face-recognition
pip install face-recognition
```

### Gemini API Errors

- Verify API key is correct in `.env`
- Check API quota at: https://console.cloud.google.com
- Ensure video files are not corrupted

### WebSocket Connection Issues

- Check firewall settings
- Ensure port 8000 is not blocked
- Try accessing from `127.0.0.1:8000` instead of `localhost:8000`

## Performance Optimization

### For Raspberry Pi or Low-Power Devices

1. Reduce video resolution:
```python
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

2. Lower FPS:
```python
camera = CameraManager(camera_source=0, fps=15)
```

3. Use low media resolution for Gemini:
```python
# In gemini_analyzer.py
video_metadata=types.VideoMetadata(fps=1, media_resolution='low')
```

### For Multiple Cameras

Create multiple `CameraManager` instances:
```python
camera1 = CameraManager(camera_source=0)
camera2 = CameraManager(camera_source=1)
```

## Security Considerations

- This system stores biometric data (face encodings)
- Ensure compliance with local privacy laws
- Use HTTPS in production
- Implement user authentication
- Encrypt the database in production
- Regularly audit stored data

## Future Enhancements

- [ ] Multi-camera support
- [ ] Person name labeling interface
- [ ] Export reports (PDF/CSV)
- [ ] Email/SMS alerts
- [ ] Integration with access control systems
- [ ] Cloud database option
- [ ] Mobile app
- [ ] Advanced analytics dashboard

## License

This project is for educational and research purposes. Ensure compliance with privacy laws and regulations in your jurisdiction.

## Credits

- **Face Recognition**: [face_recognition](https://github.com/ageitgey/face_recognition)
- **AI Analysis**: Google Gemini API
- **Web Framework**: FastAPI
- **Computer Vision**: OpenCV

## Support

For issues or questions, please check:
- Face Recognition: https://github.com/ageitgey/face_recognition/issues
- Gemini API Docs: https://ai.google.dev/docs
- FastAPI Docs: https://fastapi.tiangolo.com/
