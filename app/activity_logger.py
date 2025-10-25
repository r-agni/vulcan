"""
Activity Logger - Real-time system activity broadcasting
Streams all system activities to connected WebSocket clients
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
from fastapi import WebSocket
import json


class ActivityLogger:
    """Centralized activity logging and broadcasting system"""

    def __init__(self, max_history: int = 100):
        """
        Initialize activity logger

        Args:
            max_history: Maximum number of activity logs to keep in memory
        """
        self.max_history = max_history
        self.activity_history: List[Dict[str, Any]] = []
        self.active_connections: List[WebSocket] = []
        self.loop = None

    def log(self, message: str, category: str = "system", metadata: Dict[str, Any] = None):
        """
        Log an activity message

        Args:
            message: The activity message
            category: Category of activity (system, detection, analysis, zone, etc.)
            metadata: Optional metadata dictionary
        """
        activity = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "category": category,
            "metadata": metadata or {}
        }

        # Add to history
        self.activity_history.append(activity)

        # Trim history if needed
        if len(self.activity_history) > self.max_history:
            self.activity_history = self.activity_history[-self.max_history:]

        # Broadcast to connected clients
        self._broadcast_sync(activity)

    def _broadcast_sync(self, activity: Dict[str, Any]):
        """
        Synchronously broadcast activity to all connected clients
        Handles async event loop creation if needed
        """
        if self.active_connections:
            try:
                # Try to get the current event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create task
                        asyncio.create_task(self._broadcast_async(activity))
                    else:
                        # If loop exists but not running, run until complete
                        loop.run_until_complete(self._broadcast_async(activity))
                except RuntimeError:
                    # No event loop, create new one and run
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._broadcast_async(activity))
            except Exception as e:
                print(f"Error broadcasting activity: {e}")

    async def _broadcast_async(self, activity: Dict[str, Any]):
        """
        Asynchronously broadcast activity to all connected WebSocket clients
        """
        message = json.dumps({"type": "activity", "data": activity})
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    async def connect(self, websocket: WebSocket):
        """Add a WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

        # Send recent history to new connection
        for activity in self.activity_history[-20:]:  # Last 20 activities
            try:
                await websocket.send_text(json.dumps({"type": "activity", "data": activity}))
            except Exception as e:
                print(f"Error sending history: {e}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def get_recent_activities(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity logs"""
        return self.activity_history[-limit:]

    def clear_history(self):
        """Clear activity history"""
        self.activity_history.clear()


class AnalysisStreamer:
    """Stream Gemini analysis text in real-time"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Add a WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def stream_text(self, text: str, analysis_id: str = None, is_complete: bool = False):
        """
        Stream analysis text to all connected clients

        Args:
            text: The analysis text chunk
            analysis_id: Unique ID for this analysis session
            is_complete: Whether this is the final chunk
        """
        if self.active_connections:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._stream_async(text, analysis_id, is_complete))
                else:
                    loop.run_until_complete(self._stream_async(text, analysis_id, is_complete))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._stream_async(text, analysis_id, is_complete))
            except Exception as e:
                print(f"Error streaming analysis: {e}")

    async def _stream_async(self, text: str, analysis_id: str, is_complete: bool):
        """Asynchronously stream analysis text"""
        message = json.dumps({
            "type": "analysis_stream",
            "data": {
                "text": text,
                "analysis_id": analysis_id,
                "is_complete": is_complete,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Failed to stream to WebSocket: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


# Global instances
activity_logger = ActivityLogger()
analysis_streamer = AnalysisStreamer()


# Convenience functions for easy access
def log_activity(message: str, category: str = "system", metadata: Dict[str, Any] = None):
    """Log a system activity"""
    activity_logger.log(message, category, metadata)


def stream_analysis(text: str, analysis_id: str = None, is_complete: bool = False):
    """Stream analysis text"""
    analysis_streamer.stream_text(text, analysis_id, is_complete)
