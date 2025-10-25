"""
Video Overlay Rendering System
Draws analytics visualizations on video frames
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class VideoOverlayRenderer:
    """Render analytics overlays on video frames"""

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.overlay_config = {
            'bounding_boxes': True,
            'trajectories': True,
            'zones': True,
            'heatmap': False,
            'virtual_lines': True,
            'proximity': True,
            'labels': True,
            'alerts': True
        }

    def render_frame(
        self,
        frame: np.ndarray,
        analytics_data: Dict
    ) -> np.ndarray:
        """
        Render all enabled overlays on frame

        analytics_data structure:
        {
            'detections': [(person_id, bbox, name, zone_id, dwell_time), ...],
            'trajectories': {person_id: [points], ...},
            'zones': [{'id': 1, 'polygon': [...], 'color': '#00FF00', 'name': '...', 'occupancy': 5}, ...],
            'virtual_lines': [{'id': 1, 'start': {...}, 'end': {...}, 'counts': {...}}, ...],
            'queues': [{'zone_id': 1, 'length': 5, 'positions': [...]}, ...],
            'heatmap': np.ndarray or None,
            'alerts': [{'type': 'queue', 'message': '...'}, ...]
        }
        """
        overlay = frame.copy()

        # Layer 1: Heatmap (if enabled)
        if self.overlay_config['heatmap'] and analytics_data.get('heatmap') is not None:
            overlay = self._draw_heatmap_overlay(overlay, analytics_data['heatmap'])

        # Layer 2: Zones (if enabled)
        if self.overlay_config['zones'] and analytics_data.get('zones'):
            overlay = self._draw_zones(overlay, analytics_data['zones'])

        # Layer 3: Virtual Lines (if enabled)
        if self.overlay_config['virtual_lines'] and analytics_data.get('virtual_lines'):
            overlay = self._draw_virtual_lines(overlay, analytics_data['virtual_lines'])

        # Layer 4: Trajectories (if enabled)
        if self.overlay_config['trajectories'] and analytics_data.get('trajectories'):
            overlay = self._draw_trajectories(overlay, analytics_data['trajectories'])

        # Layer 5: Bounding Boxes (if enabled)
        if self.overlay_config['bounding_boxes'] and analytics_data.get('detections'):
            overlay = self._draw_bounding_boxes(overlay, analytics_data['detections'])

        # Layer 6: Queue Visualization
        if analytics_data.get('queues'):
            overlay = self._draw_queues(overlay, analytics_data['queues'])

        # Layer 7: Labels and Metrics (if enabled)
        if self.overlay_config['labels']:
            overlay = self._draw_labels(overlay, analytics_data)

        # Layer 8: Alerts (if enabled)
        if self.overlay_config['alerts'] and analytics_data.get('alerts'):
            overlay = self._draw_alerts(overlay, analytics_data['alerts'])

        return overlay

    def _draw_bounding_boxes(self, frame: np.ndarray, detections: List[Tuple]) -> np.ndarray:
        """Draw bounding boxes around detected persons"""
        for detection in detections:
            person_id, bbox, name, zone_id, dwell_time = detection
            top, right, bottom, left = bbox

            # Color based on status
            if zone_id:
                color = (0, 255, 0)  # Green = in zone
            else:
                color = (0, 165, 255)  # Orange = not in zone

            # Draw box
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Draw label background
            label_height = 60 if dwell_time else 35
            cv2.rectangle(frame, (left, bottom - label_height), (right, bottom), color, cv2.FILLED)

            # Draw text
            cv2.putText(
                frame,
                name,
                (left + 6, bottom - label_height + 18),
                cv2.FONT_HERSHEY_DUPLEX,
                0.5,
                (255, 255, 255),
                1
            )

            # Draw dwell time if available
            if dwell_time:
                minutes = int(dwell_time // 60)
                seconds = int(dwell_time % 60)
                cv2.putText(
                    frame,
                    f"Dwell: {minutes}m {seconds}s",
                    (left + 6, bottom - 10),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )

        return frame

    def _draw_trajectories(self, frame: np.ndarray, trajectories: Dict[int, List]) -> np.ndarray:
        """Draw trajectory paths for persons"""
        colors = [
            (255, 0, 0),    # Blue
            (0, 255, 0),    # Green
            (0, 0, 255),    # Red
            (255, 255, 0),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Yellow
        ]

        for idx, (person_id, points) in enumerate(trajectories.items()):
            if len(points) < 2:
                continue

            color = colors[idx % len(colors)]

            # Draw path
            for i in range(len(points) - 1):
                # Convert normalized coordinates to pixels
                x1 = int(points[i]['x'] * self.width)
                y1 = int(points[i]['y'] * self.height)
                x2 = int(points[i + 1]['x'] * self.width)
                y2 = int(points[i + 1]['y'] * self.height)

                # Calculate alpha based on age (fade older points)
                alpha = 0.3 + (0.7 * (i / len(points)))
                thickness = max(1, int(2 * alpha))

                cv2.line(frame, (x1, y1), (x2, y2), color, thickness)

            # Draw start point
            start_x = int(points[0]['x'] * self.width)
            start_y = int(points[0]['y'] * self.height)
            cv2.circle(frame, (start_x, start_y), 5, color, -1)

            # Draw current position (larger circle)
            end_x = int(points[-1]['x'] * self.width)
            end_y = int(points[-1]['y'] * self.height)
            cv2.circle(frame, (end_x, end_y), 8, color, -1)
            cv2.circle(frame, (end_x, end_y), 12, color, 2)

        return frame

    def _draw_zones(self, frame: np.ndarray, zones: List[Dict]) -> np.ndarray:
        """Draw zone boundaries"""
        for zone in zones:
            polygon = zone['polygon']
            if not polygon:
                continue

            # Convert normalized coordinates to pixels
            points = np.array([
                [int(p[0] * self.width), int(p[1] * self.height)]
                for p in polygon
            ], np.int32)

            # Parse color
            color = self._hex_to_bgr(zone.get('color', '#00FF00'))

            # Draw semi-transparent filled polygon
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], color)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

            # Draw border
            cv2.polylines(frame, [points], True, color, 2)

            # Draw zone label
            centroid_x = int(np.mean([p[0] for p in points]))
            centroid_y = int(np.mean([p[1] for p in points]))

            # Label background
            label_text = f"{zone['name']}"
            (label_w, label_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                frame,
                (centroid_x - label_w // 2 - 5, centroid_y - label_h - 10),
                (centroid_x + label_w // 2 + 5, centroid_y + 5),
                color,
                -1
            )

            # Label text
            cv2.putText(
                frame,
                label_text,
                (centroid_x - label_w // 2, centroid_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            # Occupancy indicator
            if 'occupancy' in zone:
                occupancy_text = f"{zone['occupancy']} people"
                cv2.putText(
                    frame,
                    occupancy_text,
                    (centroid_x - label_w // 2, centroid_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )

        return frame

    def _draw_virtual_lines(self, frame: np.ndarray, lines: List[Dict]) -> np.ndarray:
        """Draw virtual line crossing boundaries"""
        for line in lines:
            start = line['start']
            end = line['end']

            # Convert to pixels
            x1 = int(start['x'] * self.width)
            y1 = int(start['y'] * self.height)
            x2 = int(end['x'] * self.width)
            y2 = int(end['y'] * self.height)

            color = self._hex_to_bgr(line.get('color', '#FF0000'))

            # Draw line
            cv2.line(frame, (x1, y1), (x2, y2), color, 3)

            # Draw counts
            mid_x = (x1 + x2) // 2
            mid_y = (y1 + y2) // 2

            counts = line.get('counts', {'in': 0, 'out': 0})
            label = f"In: {counts['in']}  Out: {counts['out']}"

            # Label background
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                frame,
                (mid_x - label_w // 2 - 5, mid_y - label_h - 10),
                (mid_x + label_w // 2 + 5, mid_y + 5),
                color,
                -1
            )

            cv2.putText(
                frame,
                label,
                (mid_x - label_w // 2, mid_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )

        return frame

    def _draw_heatmap_overlay(self, frame: np.ndarray, heatmap: np.ndarray) -> np.ndarray:
        """Apply heatmap overlay"""
        if heatmap.shape[:2] != (self.height, self.width):
            heatmap = cv2.resize(heatmap, (self.width, self.height))

        # Blend heatmap with frame
        if heatmap.shape[2] == 4:  # Has alpha channel
            alpha = heatmap[:, :, 3] / 255.0
            for c in range(3):
                frame[:, :, c] = frame[:, :, c] * (1 - alpha) + heatmap[:, :, c] * alpha
        else:
            frame = cv2.addWeighted(frame, 0.6, heatmap, 0.4, 0)

        return frame

    def _draw_queues(self, frame: np.ndarray, queues: List[Dict]) -> np.ndarray:
        """Draw queue visualizations"""
        for queue in queues:
            positions = queue['positions']

            # Draw queue indicator
            for idx, pos in enumerate(positions):
                x = int(pos[0] * self.width)
                y = int(pos[1] * self.height)

                # Draw queue number
                cv2.circle(frame, (x, y), 15, (0, 165, 255), 2)
                cv2.putText(
                    frame,
                    str(idx + 1),
                    (x - 8, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 165, 255),
                    2
                )

        return frame

    def _draw_labels(self, frame: np.ndarray, analytics_data: Dict) -> np.ndarray:
        """Draw info labels"""
        # Store metrics in top-left corner
        y_offset = 30
        metrics = []

        if 'total_occupancy' in analytics_data:
            metrics.append(f"Occupancy: {analytics_data['total_occupancy']}")

        if 'active_trajectories' in analytics_data:
            metrics.append(f"Tracking: {analytics_data['active_trajectories']}")

        for metric in metrics:
            cv2.putText(
                frame,
                metric,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            y_offset += 30

        return frame

    def _draw_alerts(self, frame: np.ndarray, alerts: List[Dict]) -> np.ndarray:
        """Draw alert badges"""
        y_offset = 30

        for alert in alerts:
            alert_type = alert.get('type', 'info')
            message = alert.get('message', '')

            # Color based on alert type
            if alert_type == 'queue':
                color = (0, 165, 255)  # Orange
            elif alert_type == 'capacity':
                color = (0, 0, 255)  # Red
            else:
                color = (0, 255, 255)  # Yellow

            # Draw alert box in top-right
            (text_w, text_h), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                frame,
                (self.width - text_w - 20, y_offset - text_h - 10),
                (self.width - 10, y_offset + 5),
                color,
                -1
            )

            cv2.putText(
                frame,
                message,
                (self.width - text_w - 15, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            y_offset += 40

        return frame

    def _hex_to_bgr(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to BGR tuple"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (b, g, r)  # OpenCV uses BGR

    def toggle_overlay(self, overlay_name: str, enabled: bool):
        """Enable/disable specific overlay"""
        if overlay_name in self.overlay_config:
            self.overlay_config[overlay_name] = enabled

    def get_overlay_config(self) -> Dict[str, bool]:
        """Get current overlay configuration"""
        return self.overlay_config.copy()
