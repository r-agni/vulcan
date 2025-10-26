import cv2
import os
import threading
import time
from datetime import datetime
from typing import Optional, Callable
import numpy as np
try:
    from app.utils.activity_logger import log_activity
except ImportError:
    # Fallback if activity_logger is not available
    def log_activity(msg, category="system", metadata=None):
        print(f"[{category}] {msg}")


class CameraManager:
    """Manages camera feed capture and frame extraction"""

    def __init__(self, camera_source=0, fps=30):
        self.camera_source = camera_source
        self.fps = fps
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_callbacks = []
        
        # Connection health tracking
        self.consecutive_failures = 0
        self.max_failures = 10
        self.last_url_refresh = None
        self.url_refresh_interval = 3600  # Refresh URL every hour
        self.current_stream_url = None
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0

    def _get_youtube_stream_url(self, youtube_url: str) -> str:
        """Get direct video stream URL from YouTube using yt-dlp"""
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                return info['url']
        except Exception as e:
            raise Exception(f"Failed to get YouTube stream URL: {e}")

    def _refresh_youtube_url(self) -> bool:
        """Refresh YouTube stream URL if needed"""
        try:
            if isinstance(self.camera_source, str) and ('youtube.com' in self.camera_source or 'youtu.be' in self.camera_source):
                print("Refreshing YouTube stream URL...")
                new_url = self._get_youtube_stream_url(self.camera_source)
                self.current_stream_url = new_url
                self.last_url_refresh = time.time()
                
                # Reconnect with new URL
                if self.cap:
                    self.cap.release()
                self.cap = cv2.VideoCapture(new_url)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                
                if self.cap.isOpened():
                    print("Stream URL refreshed successfully")
                    self.consecutive_failures = 0
                    self.reconnect_delay = 1.0
                    return True
                else:
                    print("Failed to open stream with new URL")
                    return False
            return True
        except Exception as e:
            print(f"Error refreshing YouTube URL: {e}")
            return False

    def _validate_frame(self, frame: np.ndarray) -> bool:
        """Validate frame integrity"""
        if frame is None:
            return False
        
        # Check if frame has valid shape
        if len(frame.shape) != 3:
            return False
        
        # Check if frame has reasonable dimensions
        height, width, channels = frame.shape
        if height < 100 or width < 100 or channels != 3:
            return False
        
        # Check if frame is not completely black or corrupted
        mean_value = np.mean(frame)
        if mean_value < 1 or mean_value > 254:
            return False
        
        return True

    def start(self):
        """Start camera capture"""
        if self.is_running:
            return

        # Check if camera_source is a YouTube URL
        source = self.camera_source
        if isinstance(source, str) and ('youtube.com' in source or 'youtu.be' in source):
            print("Detected YouTube URL, extracting stream URL...")
            source = self._get_youtube_stream_url(source)
            self.current_stream_url = source
            self.last_url_refresh = time.time()
            print(f"Stream URL obtained")

        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            raise Exception(f"Cannot open camera source: {self.camera_source}")

        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        print(f"Camera started: {self.camera_source}")
        log_activity(f"🎥 Camera started - Source: {self.camera_source[:60]}...", "system")

    def stop(self):
        """Stop camera capture"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print("Camera stopped")

    def _capture_loop(self):
        """Internal loop to capture frames with robust error handling"""
        while self.is_running:
            try:
                # Check if URL needs refresh (for YouTube streams)
                if (self.last_url_refresh is not None and 
                    time.time() - self.last_url_refresh > self.url_refresh_interval):
                    print("URL refresh interval reached, refreshing...")
                    self._refresh_youtube_url()
                
                # Attempt to read frame
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Validate frame integrity
                    if self._validate_frame(frame):
                        with self.frame_lock:
                            self.current_frame = frame
                        
                        # Reset failure counter on success
                        self.consecutive_failures = 0
                        self.reconnect_delay = 1.0
                        
                        # Notify callbacks
                        for callback in self.frame_callbacks:
                            try:
                                callback(frame.copy())
                            except Exception as e:
                                print(f"Frame callback error: {e}")
                    else:
                        # Frame validation failed - corrupted frame
                        self.consecutive_failures += 1
                        if self.consecutive_failures % 5 == 0:
                            print(f"Warning: {self.consecutive_failures} consecutive corrupted frames")
                else:
                    # Failed to read frame
                    self.consecutive_failures += 1
                    print(f"Failed to read frame (attempt {self.consecutive_failures}/{self.max_failures})")
                    
                    # Check if we've exceeded max failures
                    if self.consecutive_failures >= self.max_failures:
                        print("Max failures reached, attempting reconnection...")
                        
                        # Try to refresh URL and reconnect
                        if self._refresh_youtube_url():
                            print("Reconnection successful")
                            self.consecutive_failures = 0
                            self.reconnect_delay = 1.0
                        else:
                            # Exponential backoff
                            print(f"Reconnection failed, waiting {self.reconnect_delay:.1f}s before retry...")
                            time.sleep(self.reconnect_delay)
                            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                            self.consecutive_failures = 0  # Reset to try again
                    else:
                        # Brief pause before retry
                        time.sleep(0.1)
                
                # Sleep to maintain FPS
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                # Catch any unexpected errors (TLS, socket, decoding errors)
                self.consecutive_failures += 1
                print(f"Error in capture loop: {e}")
                
                # Attempt recovery if failures accumulate
                if self.consecutive_failures >= self.max_failures:
                    print("Attempting recovery from error...")
                    try:
                        self._refresh_youtube_url()
                    except Exception as refresh_error:
                        print(f"Recovery failed: {refresh_error}")
                        time.sleep(self.reconnect_delay)
                        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                    self.consecutive_failures = 0
                else:
                    time.sleep(0.1)

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def register_frame_callback(self, callback: Callable):
        """Register a callback to be called on each new frame"""
        self.frame_callbacks.append(callback)

    def save_frame(self, frame: np.ndarray, directory: str = "data/uploads/frames") -> str:
        """Save a frame to disk"""
        os.makedirs(directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{timestamp}.jpg"
        filepath = os.path.join(directory, filename)
        cv2.imwrite(filepath, frame)
        return filepath

    def record_clip(self, duration: int = 10, output_dir: str = "data/temp_videos") -> str:
        """Record a video clip of specified duration"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"clip_{timestamp}.mp4"
        filepath = os.path.join(output_dir, filename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filepath, fourcc, self.fps, (1280, 720))

        start_time = time.time()
        while time.time() - start_time < duration:
            frame = self.get_current_frame()
            if frame is not None:
                out.write(frame)
            time.sleep(1.0 / self.fps)

        out.release()
        return filepath

    def encode_frame_to_jpg(self, frame: np.ndarray, quality: int = 85) -> bytes:
        """Encode frame to JPEG bytes for streaming"""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
        return encoded_img.tobytes() if result else None
