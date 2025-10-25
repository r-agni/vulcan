import cv2
import os
import threading
import time
from datetime import datetime
from typing import Optional, Callable
import numpy as np


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

    def start(self):
        """Start camera capture"""
        if self.is_running:
            return

        self.cap = cv2.VideoCapture(self.camera_source)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            raise Exception(f"Cannot open camera source: {self.camera_source}")

        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        print(f"Camera started: {self.camera_source}")

    def stop(self):
        """Stop camera capture"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print("Camera stopped")

    def _capture_loop(self):
        """Internal loop to capture frames"""
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.current_frame = frame

                # Notify callbacks
                for callback in self.frame_callbacks:
                    try:
                        callback(frame.copy())
                    except Exception as e:
                        print(f"Frame callback error: {e}")
            else:
                print("Failed to read frame")
                time.sleep(0.1)

            time.sleep(1.0 / self.fps)

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def register_frame_callback(self, callback: Callable):
        """Register a callback to be called on each new frame"""
        self.frame_callbacks.append(callback)

    def save_frame(self, frame: np.ndarray, directory: str = "uploads/frames") -> str:
        """Save a frame to disk"""
        os.makedirs(directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{timestamp}.jpg"
        filepath = os.path.join(directory, filename)
        cv2.imwrite(filepath, frame)
        return filepath

    def record_clip(self, duration: int = 10, output_dir: str = "temp_videos") -> str:
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
