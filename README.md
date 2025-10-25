# Video AI Surveillance System

An intelligent retail surveillance system powered by Google Gemini AI, providing real-time person detection, behavioral analysis, and actionable alerts for store staff.

---

## 1. Problem & Overview

### The Problem

Traditional retail surveillance systems face critical limitations:

- **Passive Monitoring**: Cameras record footage but provide no real-time insights or actionable intelligence
- **Missed Opportunities**: Customers showing interest in products often leave without assistance because staff are unaware
- **Inefficient Operations**: Long queues, overcrowding, and bottlenecks go unnoticed until it's too late
- **Manual Review**: Hours spent reviewing footage manually to understand customer behavior patterns
- **No Behavioral Intelligence**: Unable to detect customer emotions, confusion, or purchase intent in real-time

### Our Solution

This Video AI Surveillance System transforms passive cameras into an intelligent retail assistant that:

- **Detects and tracks** people in real-time with computer vision
- **Analyzes behavior** using Google Gemini AI to understand customer emotions, intent, and patterns
- **Generates intelligent alerts** for salespeople (customer engagement opportunities) and managers (operational issues)
- **Provides historical insights** through RAG-powered natural language search over all analytics
- **Visualizes analytics** with live dashboards showing heatmaps, trajectories, zones, and metrics

---

## 2. What This Solution Does

### Core Capabilities

1. **Real-Time Person Detection & Tracking**
   - Detects people in video streams using YOLOv8
   - Tracks movement trajectories across the store
   - Identifies which zones customers visit and for how long

2. **AI-Powered Zone Generation**
   - Gemini automatically analyzes store layout from video
   - Generates tracking zones (entrance, checkout, product areas, aisles)
   - Creates virtual counting lines for entry/exit tracking

3. **Comprehensive Retail Analytics**
   - **Trajectory Tracking**: Path visualization of customer movement
   - **Dwell Time Analysis**: Time spent in each zone
   - **Occupancy Counting**: Real-time customer count per zone
   - **Traffic Heatmaps**: Identify high-traffic and dead zones
   - **Line Crossing Detection**: Count entries, exits, and zone transitions
   - **Queue Detection**: Identify queue formations and wait times

4. **Gemini Behavioral Analysis**
   - Analyzes video frames every 5 seconds for behavioral insights
   - Detects emotions (frustration, confusion, interest)
   - Identifies shopping patterns (browsing vs. purposeful shopping)
   - Assesses purchase intent based on customer behavior

5. **Intelligent Alert System**
   - **For Salespeople**: Customer engagement opportunities (high interest, needs assistance, premium customers)
   - **For Managers**: Operational issues (long queues, capacity warnings, system alerts)
   - Includes person-specific details (appearance, behavior history, recommended approach)
   - Smart deduplication and prioritization

6. **RAG-Powered Historical Search**
   - Natural language queries over all historical analytics
   - Search past behavior analysis, zone activity, customer patterns
   - Powered by ChromaDB vector store with semantic search

7. **Live Dashboard**
   - Real-time video feed with configurable overlays
   - Live metrics (occupancy, dwell time, entries, peak traffic)
   - System activity feed and Gemini analysis stream
   - Alert notifications with priority indicators
   - RAG search interface

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          VIDEO INPUT LAYER                              │
│  ┌──────────────┐              ┌──────────────┐                        │
│  │   YouTube    │              │  Local Video │                        │
│  │   Stream     │              │     File     │                        │
│  └──────┬───────┘              └──────┬───────┘                        │
│         └──────────────┬───────────────┘                                │
└────────────────────────┼────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       DETECTION LAYER                                   │
│                  ┌─────────────────────┐                                │
│                  │   Camera Manager    │                                │
│                  │  (Frame Callbacks)  │                                │
│                  └──────────┬──────────┘                                │
│                             │                                            │
│                  ┌──────────▼──────────┐                                │
│                  │  Person Detector    │                                │
│                  │  (YOLOv8/OpenCV)    │                                │
│                  └──────────┬──────────┘                                │
└─────────────────────────────┼────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   RETAIL ANALYTICS       │    │   GEMINI ANALYZER        │
│   ┌──────────────────┐   │    │  (Every 5 seconds)       │
│   │ Trajectory Track │   │    │  ┌────────────────────┐  │
│   │ Dwell Calculator │   │    │  │ Frame Analysis     │  │
│   │ Zone Detector    │   │    │  │ Behavior Insights  │  │
│   │ Occupancy Count  │   │    │  │ Emotion Detection  │  │
│   │ Line Crossing    │   │    │  │ Zone Generation    │  │
│   │ Heatmap Gen      │   │    │  └─────────┬──────────┘  │
│   │ Queue Detector   │   │    │            │              │
│   └─────────┬────────┘   │    └────────────┼──────────────┘
└─────────────┼────────────┘                 │
              │                              │
              └──────────┬───────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ALERT GENERATION LAYER                             │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                     Alert Generator                             │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │    │
│  │  │ Rule-Based   │  │ Behavior     │  │ AI-Generated         │ │    │
│  │  │ Alerts       │  │ Analysis     │  │ (Gemini)             │ │    │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────────────┘ │    │
│  │         └──────────────────┼──────────────────┘                 │    │
│  │                            ▼                                    │    │
│  │                   ┌─────────────────┐                           │    │
│  │                   │  Alert Manager  │                           │    │
│  │                   │  (Dedupe/Queue) │                           │    │
│  │                   └────────┬────────┘                           │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────┬───────────────────────────┘
                                              │
              ┌───────────────────────────────┼───────────────┐
              ▼                               ▼               ▼
┌────────────────────┐         ┌─────────────────────┐  ┌─────────────┐
│  STORAGE LAYER     │         │    API LAYER        │  │ RAG SYSTEM  │
│ ┌────────────────┐ │         │  ┌──────────────┐   │  │┌───────────┐│
│ │ SQLAlchemy DB  │ │         │  │   FastAPI    │   │  ││ ChromaDB  ││
│ │ - Analytics    │ │◄────────┤  │   (REST +    │   │  ││ Vector    ││
│ │ - Detections   │ │         │  │  WebSocket)  │   │  ││ Store     ││
│ │ - Zones/Lines  │ │         │  └──────┬───────┘   │  │└─────┬─────┘│
│ │ - Behavior     │ │         │         │           │  │      │      │
│ └────────────────┘ │         └─────────┼───────────┘  │┌─────▼─────┐│
└────────────────────┘                   │              ││  Query    ││
                                         │              ││  Engine   ││
                                         ▼              │└───────────┘│
                            ┌──────────────────────┐   └─────────────┘
                            │  FRONTEND LAYER      │
                            │  ┌────────────────┐  │
                            │  │   Dashboard    │  │
                            │  │  - Video Feed  │  │
                            │  │  - Metrics     │  │
                            │  │  - Alerts      │  │
                            │  │  - Analytics   │  │
                            │  │  - RAG Search  │  │
                            │  └────────────────┘  │
                            └──────────────────────┘
```

---

## 4. Agentic Workflow Diagram

This system operates as a multi-agent intelligent platform where specialized agents collaborate:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENT AGENT WORKFLOW                       │
└─────────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐
   │ VIDEO INPUT  │
   │   AGENT      │
   │ (Camera Mgr) │
   └──────┬───────┘
          │ Frame Callback
          │ (Real-time)
          ▼
   ┌──────────────────────┐
   │   DETECTION AGENT    │
   │   (YOLOv8 Person     │
   │    Detector)         │
   │                      │
   │ Output: Bounding     │
   │ boxes, person IDs,   │
   │ confidence scores    │
   └──────┬───────────────┘
          │
          │ Detections
          │
   ┌──────┴──────────────────────────────────────────────┐
   │                                                      │
   ▼                                                      ▼
┌──────────────────────────┐                 ┌────────────────────────┐
│  RETAIL ANALYTICS        │                 │  GEMINI ANALYSIS       │
│  AGENTS (7 specialized)  │                 │  AGENT                 │
│                          │                 │                        │
│  1. Trajectory Tracker   │                 │  Analyzes frame every  │
│     - Tracks paths       │                 │  5 seconds:            │
│     - Session IDs        │                 │  • Frame analysis      │
│                          │                 │  • Behavioral insights │
│  2. Dwell Calculator     │                 │  • Emotion detection   │
│     - Time in zones      │                 │  • Purchase intent     │
│     - Engagement score   │                 │  • Confusion signals   │
│                          │                 │                        │
│  3. Zone Detector        │                 │  Output:               │
│     - Point-in-polygon   │                 │  • Analysis text       │
│     - Zone identification│                 │  • Timestamps          │
│                          │                 │  • Context data        │
│  4. Occupancy Counter    │                 └────────┬───────────────┘
│     - Real-time counts   │                          │
│     - Per-zone tracking  │                          │ Saves to DB
│                          │                          │
│  5. Line Crossing Det.   │                          ▼
│     - Entry/exit counts  │                 ┌────────────────────────┐
│     - Direction tracking │                 │  DOCUMENT INDEXER      │
│                          │                 │  AGENT                 │
│  6. Heatmap Generator    │                 │                        │
│     - Traffic patterns   │                 │  • Embeds analysis     │
│     - Visualization      │                 │  • Stores in ChromaDB  │
│                          │                 │  • Enables RAG search  │
│  7. Queue Detector       │                 └────────────────────────┘
│     - Formation detect   │
│     - Wait time calc     │
│                          │
│  Output: Analytics data  │
└──────┬───────────────────┘
       │
       │ Analytics + Behavior Data
       │
       ▼
┌───────────────────────────────────────────────────────────────────┐
│              ALERT GENERATION AGENT (Gemini-Powered)              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Input: Analytics data + Gemini behavior analysis       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Step 1: RULE-BASED ALERT ENGINE                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  • Alert Rules Agent processes:                        │     │
│  │    - Dwell time thresholds (2min, 5min, 10min, 15min) │     │
│  │    - Queue length warnings (5+, 7+ people)             │     │
│  │    - Occupancy capacity alerts (75%, 90%)              │     │
│  │    - Zone-specific rules                               │     │
│  │                                                         │     │
│  │  Output: Rule-based alerts                             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  Step 2: BEHAVIOR ANALYSIS ALERT ENGINE                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  • Parses Gemini analysis text for patterns:           │     │
│  │    - Confusion indicators (looking around, hesitant)   │     │
│  │    - Assistance needed (examining products)            │     │
│  │    - High-value opportunities (premium section)        │     │
│  │    - Negative emotions (frustrated, impatient)         │     │
│  │                                                         │     │
│  │  Output: Behavior-triggered alerts                     │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  Step 3: AI-GENERATED CONTEXTUAL ALERT ENGINE                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  • Gemini analyzes complete context:                   │     │
│  │    - All zone occupancy data                           │     │
│  │    - Dwell time patterns                               │     │
│  │    - Queue metrics                                     │     │
│  │    - Behavior analysis insights                        │     │
│  │    - Person tracking history                           │     │
│  │                                                         │     │
│  │  • Generates 5-8 intelligent alerts with:              │     │
│  │    - Priority (low/medium/high/critical)               │     │
│  │    - Category (customer_service/queue/security/ops)    │     │
│  │    - Recipient (salesperson/manager/both)              │     │
│  │    - Person details (demographics, appearance,         │     │
│  │      behavior, zone history, engagement level,         │     │
│  │      purchase intent, recommended approach)            │     │
│  │                                                         │     │
│  │  Focus: 70-80% salesperson alerts for customer         │     │
│  │         engagement opportunities                        │     │
│  │                                                         │     │
│  │  Output: AI-generated contextual alerts                │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  Combined Output: List of Alert objects                          │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   ALERT MANAGER AGENT   │
                    │                         │
                    │  • Deduplication        │
                    │    - Signature-based    │
                    │    - 5-minute window    │
                    │                         │
                    │  • Prioritization       │
                    │    - Critical first     │
                    │    - Timestamp ordering │
                    │                         │
                    │  • Lifecycle Mgmt       │
                    │    - Active queue       │
                    │    - Acknowledgment     │
                    │    - Expiration (10min) │
                    │    - History tracking   │
                    │                         │
                    │  • Queue Management     │
                    │    - Max 50 alerts      │
                    │    - Auto-trim          │
                    │                         │
                    │  Output: Prioritized    │
                    │  alert queue            │
                    └───────┬─────────────────┘
                            │
                            │ WebSocket broadcast
                            │
                ┌───────────┴──────────┐
                │                      │
                ▼                      ▼
    ┌────────────────────┐   ┌────────────────────┐
    │  DASHBOARD AGENT   │   │   RAG QUERY AGENT  │
    │                    │   │                    │
    │  WebSocket clients:│   │  • Query Engine    │
    │  • Video feed      │   │  • Vector search   │
    │  • Metrics stream  │   │  • Gemini LLM      │
    │  • Activity feed   │   │                    │
    │  • Analysis stream │   │  Answers questions │
    │  • Alert stream    │   │  about historical  │
    │                    │   │  data              │
    │  Real-time UI      │   │                    │
    │  updates           │   │  "Show me all      │
    │                    │   │   frustrated       │
    │                    │   │   customers today" │
    └────────────────────┘   └────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                     KEY AGENTIC BEHAVIORS                               │
├─────────────────────────────────────────────────────────────────────────┤
│  • Autonomous Operation: All agents run continuously without manual     │
│    intervention                                                         │
│                                                                          │
│  • Intelligent Decision Making: Gemini agents use context to make       │
│    nuanced decisions (e.g., salesperson vs manager alerts)              │
│                                                                          │
│  • Adaptive Learning: System learns from patterns (zone generation,     │
│    dwell time thresholds adapt to store type)                           │
│                                                                          │
│  • Collaborative Intelligence: Multiple agents share data and context   │
│    (analytics → alert generation → alert management → delivery)         │
│                                                                          │
│  • Goal-Oriented: Each agent has clear objectives:                      │
│    - Detection Agent: Maximize accuracy                                 │
│    - Analytics Agents: Track metrics comprehensively                    │
│    - Alert Agent: Identify actionable opportunities                     │
│    - Manager Agent: Prevent alert fatigue through deduplication         │
│    - RAG Agent: Surface relevant historical insights                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Features (In Detail)

### 5.1 Real-Time Person Detection & Tracking

- **Technology**: YOLOv8-based person detection via `facenet-pytorch`
- **Confidence Threshold**: Configurable (default 70%)
- **Bounding Box Tracking**: Assigns unique IDs to each detected person
- **Frame Processing**: Real-time callback system for continuous monitoring
- **Performance**: Processes video streams at camera FPS

**Use Cases**:
- Count customers in store at any moment
- Track individual customer journeys
- Identify high-traffic periods

### 5.2 Gemini AI-Powered Zone Generation

- **Automatic Layout Analysis**: Gemini analyzes store video to understand layout
- **Zone Types**: Entrance, Checkout, Product, Aisle, Queue
- **Smart Polygon Generation**: Creates 4-8 optimal tracking zones with normalized coordinates (0-1)
- **Virtual Line Placement**: Automatically places counting lines at entry/exit points
- **Configuration Output**: JSON format ready for database storage

**Generated Data**:
```json
{
  "zones": [
    {
      "name": "Main Entrance",
      "zone_type": "entrance",
      "polygon_points": [[0.1, 0.2], [0.3, 0.2], [0.3, 0.5], [0.1, 0.5]],
      "color": "#00FF00",
      "max_capacity": 10
    }
  ],
  "virtual_lines": [
    {
      "name": "Entry Counter",
      "start_point": {"x": 0.15, "y": 0.3},
      "end_point": {"x": 0.25, "y": 0.3},
      "count_direction": "both"
    }
  ]
}
```

### 5.3 Comprehensive Retail Analytics Suite

#### 5.3.1 Trajectory Tracking
- **History Duration**: Configurable (default 60 seconds)
- **Path Visualization**: Renders movement trails on video overlay
- **Session Tracking**: UUID-based session management
- **Database Storage**: Full path history saved to DB

#### 5.3.2 Dwell Time Analysis
- **Per-Zone Tracking**: Calculates time spent in each zone
- **Real-Time Updates**: Live dwell time calculation
- **Engagement Scoring**: Optional engagement metrics
- **Alert Triggers**: Automatically alerts on extended dwell (2min, 5min, 10min thresholds)

#### 5.3.3 Occupancy Counting
- **Zone-Specific**: Tracks occupancy per zone
- **Total Store Count**: Overall customer count
- **Capacity Management**: Alerts when approaching max capacity (75%, 90%)
- **Real-Time Updates**: Instant occupancy changes broadcast via WebSocket

#### 5.3.4 Traffic Heatmaps
- **Resolution**: Configurable grid (default 20px cells)
- **Gaussian Smoothing**: Beautiful gradient visualization
- **Colormap**: Blue → Green → Yellow → Red (low to high traffic)
- **Accumulation**: Builds heatmap over time
- **Use Case**: Identify dead zones and high-traffic areas for layout optimization

#### 5.3.5 Line Crossing Detection
- **Direction Tracking**: In, Out, or Both
- **Crossing Counts**: Maintains cumulative counts per line
- **Event Logging**: Saves each crossing event to database
- **Applications**: Entry/exit counting, zone transition tracking

#### 5.3.6 Queue Detection
- **Proximity Clustering**: Groups people within threshold distance
- **Linear Formation Detection**: Identifies queue-like patterns
- **Minimum Queue Length**: Configurable (default 3 people)
- **Wait Time Estimation**: Calculates average wait time
- **Alert Triggers**: Long queues (5+, 7+ people) generate manager alerts

### 5.4 Gemini Behavioral Analysis

Runs continuously every 5 seconds to analyze current frame:

**Analysis Dimensions**:
1. **Person Description**: Appearance, clothing, age estimate, gender
2. **Emotional State**: Facial expressions, body language, mood indicators
3. **Movement Patterns**: Walking speed, gait, stopping points
4. **Areas of Interest**: Products examined, duration of attention
5. **Actions**: Interactions with environment, unusual behaviors
6. **Timestamps**: Key moments with MM:SS format

**Specialized Analyses**:
- **Shopping Behavior Analysis**: Purchase intent signals, product examination
- **Queue Experience Analysis**: Patience level, abandonment risk
- **Layout Effectiveness**: Navigation efficiency, confusion points
- **Product Interaction**: Engagement level, decision-making process

**Streaming**: Results streamed in real-time to dashboard via WebSocket

### 5.5 Intelligent Alert System

#### Alert Types

##### Rule-Based Alerts (Fast, Deterministic)
- **Dwell Time Alerts**:
  - 2 min: "Customer showing interest" (Medium priority, Salesperson)
  - 5 min: "Customer may need assistance" (Medium priority, Salesperson)
  - 10 min: "High interest customer" (High priority, Salesperson)
  - 15 min: "Unusual dwell time" (High priority, Manager)

- **Queue Alerts**:
  - 5+ customers: "Queue building up" (High priority, Manager)
  - 7+ customers: "Critical queue length" (Critical priority, Manager)

- **Occupancy Alerts**:
  - 75% capacity: "High occupancy" (High priority, Manager)
  - 90% capacity: "Near capacity" (Critical priority, Manager)

##### Behavior-Based Alerts (Pattern Recognition)
- Confusion detected: "Customer appears to need assistance" (Medium, Salesperson)
- High product engagement: "Customer may need product assistance" (Medium, Salesperson)
- Premium customer: "High-value customer opportunity" (High, Both)
- Negative emotions: "Customer showing negative emotions" (High, Manager)

##### AI-Generated Alerts (Contextual Intelligence)
Gemini analyzes complete context and generates 5-8 alerts per cycle:

**Example Alert**:
```json
{
  "title": "Person #42 in Electronics",
  "message": "Customer examining premium laptops for 8 minutes",
  "priority": "high",
  "category": "customer_service",
  "recipient": "salesperson",
  "person_id": 42,
  "zone_name": "Electronics",
  "person_details": {
    "estimated_demographics": "Male, 30-40 years old",
    "appearance": "Business casual, carrying laptop bag",
    "behavior_summary": "Examining high-end laptops, comparing specs",
    "zone_history": "Entered electronics 8 min ago, previously in entrance",
    "engagement_level": "high",
    "purchase_intent": "Strong interest in premium models, likely comparing features",
    "recommended_approach": "Offer assistance with technical specifications and financing options"
  }
}
```

**Alert Distribution**:
- 70-80% for Salespeople: Customer engagement opportunities
- 20-30% for Managers: Operational issues

#### Alert Management Features

- **Smart Deduplication**: Signature-based (category + recipient + zone + title)
- **5-Minute Cooldown**: Same alert won't repeat within 5 minutes
- **Priority Queue**: Critical → High → Medium → Low
- **Max Queue Size**: 50 alerts (auto-trim oldest low-priority)
- **Lifecycle States**: Active → Acknowledged → Expired/Dismissed
- **Auto-Expiration**: Alerts expire after 10 minutes if not acknowledged
- **WebSocket Delivery**: Real-time push to dashboard

### 5.6 RAG-Powered Historical Search

**Technology Stack**:
- **Vector Store**: ChromaDB for embeddings
- **Embeddings**: Google Generative AI embeddings (768 dimensions)
- **Query Engine**: Gemini 2.5 Flash for answer generation
- **Document Sources**: Gemini behavior analysis + analytics data

**Capabilities**:
- Natural language questions: "Show me all frustrated customers today"
- Semantic search over historical behavior analysis
- Filters: Time range, zone ID, person ID
- Multi-turn conversations with history context
- Summary generation for time periods or zones

**API Endpoints**:
- `POST /rag/query`: Ask questions
- `POST /rag/index`: Index new data
- `GET /rag/stats`: Get database statistics
- `POST /rag/conversation`: Multi-turn dialogue

### 5.7 Live Dashboard

**Layout**:
- **Top Section**:
  - **Left (70%)**: Live video feed with overlays
  - **Right (30%)**: Real-time metrics cards

- **Bottom Section**: Tabbed panels
  - **System Activity**: Event log with timestamps
  - **Gemini Analysis**: Streaming behavioral insights
  - **RAG Search**: Natural language query interface

**Video Overlays** (Configurable):
- Bounding boxes around detected people
- Trajectories (movement trails)
- Zone boundaries with occupancy counts
- Virtual counting lines with in/out counts
- Traffic heatmap overlay
- Proximity circles
- Labels and info tags
- Alert badges on relevant people

**Real-Time Metrics**:
- Current Customers (live count)
- Peak Today (highest occupancy)
- Avg Dwell Time (across all zones)
- Active Tracking (trajectories being tracked)
- Entries Today (cumulative)
- Active Zones (number of zones)

**Alert Banner**:
- Priority-based color coding
- Icon by category
- Acknowledge/Dismiss actions
- Person details expansion
- Real-time updates via WebSocket

**WebSocket Connections**:
- `/ws/activity`: System events
- `/ws/analysis`: Gemini insights
- `/ws/metrics`: Live metrics
- `/ws/alerts`: Alert notifications

---

## 6. Technical Choices & Specifications

### Backend Framework
**FastAPI** (Python 3.9+)
- **Why**: High-performance async framework with native WebSocket support
- **Features Used**:
  - Async/await for concurrent operations
  - WebSocket for real-time streaming
  - Pydantic for data validation
  - Automatic OpenAPI documentation
  - CORS middleware for frontend integration

### Computer Vision Stack
**OpenCV** + **facenet-pytorch** (YOLOv8)
- **Why OpenCV**: Industry-standard, optimized for real-time video processing
- **Why YOLOv8**: State-of-the-art object detection with excellent person detection accuracy
- **Detection Config**:
  - Confidence threshold: 70%
  - Input resolution: 1280x720 (configurable)
  - Processing: Real-time frame callbacks

### AI/ML Platform
**Google Gemini 2.5 Flash**
- **Why Gemini**:
  - Native video understanding (no frame extraction needed)
  - Fast inference for real-time analysis
  - Strong multimodal capabilities (vision + language)
  - YouTube URL support (no download required)
  - JSON output for structured data

- **Use Cases**:
  1. Video layout analysis → zone generation
  2. Frame-by-frame behavioral analysis
  3. Alert generation with contextual intelligence
  4. RAG answer generation

### Vector Store & RAG
**ChromaDB** + **Google Generative AI Embeddings**
- **Why ChromaDB**:
  - Lightweight, embedded database
  - Fast similarity search
  - Easy Python integration
  - No separate server required

- **Embedding Model**: `models/embedding-001` (768 dimensions)
- **Query Engine**: Retrieval + Gemini for answer synthesis

### Database
**SQLAlchemy** ORM with **SQLite** (production-ready for PostgreSQL)
- **Why SQLAlchemy**:
  - ORM abstraction for easy querying
  - Database-agnostic (swap to PostgreSQL/MySQL easily)
  - Migration support
  - Session management

- **Tables**:
  - `person_trajectories`: Movement tracking
  - `dwell_time_records`: Zone dwell times
  - `zones`, `virtual_lines`: Zone configurations
  - `line_crossing_events`: Entry/exit events
  - `occupancy_logs`: Historical occupancy
  - `queue_metrics`: Queue data
  - `heatmap_data`: Traffic heatmaps
  - `behavior_analysis`: Gemini insights

### Frontend
**Vanilla JavaScript** (No frameworks)
- **Why No Framework**:
  - Lightweight, no build step
  - Direct WebSocket control
  - Fast page loads
  - Easy customization

- **WebSocket Clients**: 4 concurrent connections for different data streams
- **Rendering**: Server-side rendering for initial HTML, JS for dynamic updates

### Video Input
**yt-dlp** + **pafy** for YouTube support
- **Why yt-dlp**: Robust YouTube downloading and streaming
- **Local Files**: MP4, AVI support via OpenCV
- **YouTube URLs**: Direct streaming without download (faster startup)

### Deployment
**Uvicorn** ASGI Server
- **Host**: 0.0.0.0 (accessible on network)
- **Port**: 8000
- **Workers**: Single worker (WebSocket compatibility)
- **Reload**: Dev mode with auto-reload

### Dependencies (requirements.txt)
```
fastapi==0.104.1          # Web framework
uvicorn==0.24.0           # ASGI server
opencv-python==4.8.1.78   # Computer vision
facenet-pytorch           # YOLOv8 person detection
google-genai==0.2.0       # Gemini API
chromadb                  # Vector store (to be added)
sqlalchemy==2.0.23        # ORM
pydantic==2.5.0           # Data validation
websockets==15.0          # WebSocket support
numpy==1.26.2             # Numerical operations
scipy==1.11.4             # Scientific computing (heatmap smoothing)
yt-dlp==2023.11.16        # YouTube support
python-dotenv==1.0.0      # Environment variables
```

### Performance Characteristics
- **Frame Processing**: ~30 FPS for 720p video
- **Gemini Analysis**: Every 5 seconds (non-blocking)
- **Alert Generation**: < 2 seconds per cycle
- **WebSocket Latency**: < 100ms for real-time updates
- **RAG Query**: 1-3 seconds depending on corpus size
- **Memory**: ~2GB RAM for typical operation

---

## 7. Future Improvements

### Short-Term Enhancements

1. **Multi-Camera Support**
   - Cross-camera person re-identification using appearance features
   - Synchronized multi-angle analysis
   - Store-wide customer journey tracking

2. **Enhanced Emotion Recognition**
   - Facial expression analysis with confidence scores
   - Sentiment tracking over time
   - Correlation with purchase behavior

3. **Mobile Alert Application**
   - iOS/Android apps for salespeople
   - Push notifications for high-priority alerts
   - Quick acknowledgment interface
   - Person location on floor plan

4. **Advanced Analytics Dashboard**
   - Historical trend visualization
   - Comparative analytics (day-over-day, week-over-week)
   - Customizable reports
   - Export to PDF/Excel

### Mid-Term Enhancements

5. **Predictive Analytics**
   - Staffing optimization based on predicted traffic
   - Queue wait time prediction
   - Peak hour forecasting
   - Seasonal pattern recognition

6. **POS Integration**
   - Correlate behavior analysis with actual purchases
   - Conversion rate tracking (dwell time → purchase)
   - Product affinity analysis
   - ROI measurement for layout changes

7. **Customer Journey Mapping**
   - Cross-visit identification (returning customers)
   - Multi-day behavior patterns
   - Lifetime value estimation
   - Loyalty insights

8. **A/B Testing for Store Layout**
   - Compare traffic patterns before/after layout changes
   - Heatmap differential analysis
   - Statistical significance testing
   - Recommendation engine for optimal layout

### Long-Term Enhancements

9. **Inventory Integration**
   - Product interaction → stock level correlation
   - Out-of-stock detection from customer behavior
   - Restocking priority alerts
   - Shrinkage detection

10. **Advanced Security Features**
    - Suspicious behavior detection
    - Known shoplifter identification (privacy-compliant)
    - Unauthorized area access alerts
    - After-hours monitoring

11. **Voice Integration**
    - Voice-activated queries for staff ("How many customers in electronics?")
    - Verbal alert delivery
    - Hands-free operation

12. **Edge Deployment**
    - On-premise deployment for data privacy
    - Reduced cloud costs
    - Lower latency
    - Offline operation capability

13. **Industry-Specific Adaptations**
    - Restaurant/cafe mode (table occupancy, wait times)
    - Museum/gallery mode (exhibit engagement, crowd flow)
    - Healthcare mode (patient flow, wait room occupancy)
    - Event mode (crowd density, bottleneck detection)

### Research Directions

14. **Gaze Tracking**
    - Eye tracking for product attention
    - Display effectiveness measurement
    - Shelf placement optimization

15. **Group Behavior Analysis**
    - Family/friend group detection
    - Group decision-making patterns
    - Social influence on purchases

16. **3D Reconstruction**
    - 3D spatial mapping of store
    - Height-based customer segmentation
    - Volumetric occupancy tracking

---

## Installation & Setup

### Prerequisites
- Python 3.9+
- Webcam or video file
- Google Gemini API key

### Installation
```bash
# Clone repository
git clone <repository-url>
cd videoAI

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Running the System
```bash
# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Access dashboard
# Open browser to http://localhost:8000
```

### Configuration
- Camera source: Edit `camera_source` in [app/main.py:40](app/main.py#L40)
- Detection confidence: Edit `confidence_threshold` in [app/main.py:41](app/main.py#L41)
- Zone generation: Automatic via Gemini on startup

---

## API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Video & Detection
- `GET /video_feed`: Streaming video with overlays
- `GET /api/current_detection`: Get current detections

#### Alerts
- `GET /api/alerts`: Get active alerts
- `POST /api/alerts/{alert_id}/acknowledge`: Acknowledge alert
- `POST /api/alerts/{alert_id}/dismiss`: Dismiss alert
- `GET /api/alerts/statistics`: Get alert statistics

#### Overlay Controls
- `POST /api/overlay/toggle`: Toggle overlay layer
- `GET /api/overlay/settings`: Get overlay configuration

#### RAG System
- `POST /rag/query`: Query historical data
- `POST /rag/index`: Index new documents
- `GET /rag/stats`: Get vector store statistics

---

## License

MIT License

---

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

---

## Acknowledgments

- **Google Gemini**: For powerful multimodal AI capabilities
- **Ultralytics YOLOv8**: For state-of-the-art object detection
- **OpenCV**: For computer vision tools
- **FastAPI**: For excellent async web framework

---

**Built with AI for Intelligent Retail**
