# Video AI Dashboard - React Frontend

## Setup Complete ✅

The React project structure has been created with:
- ⚡ Vite build tool
- ⚛️ React 18
- 🐻 Zustand state management
- 🔌 Custom WebSocket hooks
- 🎨 CSS Modules for styling

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
# Start React dev server (runs on http://localhost:5173)
npm run dev

# In another terminal, start FastAPI backend
cd ..
python -m uvicorn app.main:app --reload
```

The Vite dev server will proxy API calls to FastAPI running on port 8000.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── Header/
│   │   ├── StatusIndicator/
│   │   ├── VideoSection/
│   │   ├── AlertBanner/
│   │   └── ContentPanels/
│   ├── hooks/               # Custom hooks
│   │   ├── useWebSocket.js
│   │   ├── useActivity.js
│   │   └── useMetrics.js
│   ├── store/               # Zustand store
│   │   └── dashboardStore.js
│   ├── styles/              # Global styles
│   │   └── global.css
│   ├── App.jsx              # Main app component
│   └── main.jsx             # Entry point
├── index.html
├── vite.config.js
└── package.json
```

## Components to Create

### Already Created:
- ✅ App.jsx - Main layout
- ✅ Header - Title and controls
- ✅ Zustand store with state management
- ✅ WebSocket hooks (useWebSocket, useActivity, useMetrics)

### To Create:

1. **StatusIndicator** - Connection status
2. **AlertBanner** - Alert notifications
3. **VideoSection** - Video feed with overlay metrics
4. **ContentPanels** - Container for all panels
5. **Individual Panels**:
   - ActivityPanel
   - AnalysisPanel
   - RAGSearchPanel
   - InventoryPanel
   - CustomerPanel

## State Management

Using Zustand for global state:

```javascript
import useDashboardStore from './store/dashboardStore';

// In your component
const metrics = useDashboardStore((state) => state.metrics);
const updateMetrics = useDashboardStore((state) => state.updateMetrics);
```

## WebSocket Integration

```javascript
import { useWebSocket } from './hooks/useWebSocket';

// In your component
const { isConnected } = useWebSocket('/ws/metrics', (data) => {
  // Handle incoming data
  console.log(data);
});
```

## Building for Production

```bash
npm run build
```

This creates a `dist/` folder with optimized production build.

## Integrating with FastAPI

Update `app/main.py` to serve the React build:

```python
import os
from fastapi.responses import FileResponse

# Serve React build
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        if full_path.startswith(("api/", "ws/", "video_feed", "rag/")):
            raise HTTPException(status_code=404)
        return FileResponse("frontend/dist/index.html")
```

## Next Steps

1. **Install dependencies**: `cd frontend && npm install`
2. **Create remaining components** (StatusIndicator, VideoSection, Panels)
3. **Add additional WebSocket hooks** (useAnalysis, useAlerts, useInventory, useCustomers)
4. **Test with backend**: `npm run dev` + run FastAPI
5. **Build for production**: `npm run build`
6. **Update FastAPI** to serve React build

## Styling

Using CSS Modules - each component has its own `.module.css` file:

```jsx
import styles from './Component.module.css';

<div className={styles.container}>...</div>
```

Global variables are available in all components from `styles/global.css`.

## Features

- ✅ Real-time WebSocket connections
- ✅ Auto-reconnection on disconnect
- ✅ Global state management with Zustand
- ✅ Component-based architecture
- ✅ CSS Modules for scoped styling
- ✅ Hot module replacement (HMR)
- ✅ Production build optimization

## Migration from Static HTML

The old dashboard (`static/dashboard.html`) will remain as backup. Once React version is complete and tested, update FastAPI routing to serve React as the primary interface.
