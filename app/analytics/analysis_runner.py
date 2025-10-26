#!/usr/bin/env python3
"""
Comprehensive Video Analysis Runner
Runs all analysis modules: person detection, face recognition, Gemini AI, and retail analytics
"""

import cv2
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import numpy as np
from sqlalchemy.orm import Session
import time

from app.core.database import init_db, get_db, Person, DetectionEvent, SessionLocal, BodyDetectionEvent, PersonSession
from app.video.camera_manager import CameraManager
from app.detection.person_detector import PersonDetector
from app.detection.face_detector import FaceDetector
from app.analytics.gemini_analyzer import GeminiAnalyzer
from app.detection.body_tracker import BodyTracker
from app.analytics.retail_analytics import (
    TrajectoryTracker, DwellTimeCalculator, ZoneDetector,
    OccupancyCounter, LineCrossingDetector, HeatmapGenerator, QueueDetector
)
from dotenv import load_dotenv

load_dotenv()


class ComprehensiveAnalysisRunner:
    """Orchestrates all analysis components"""

    def __init__(
        self,
        video_source: str,
        output_dir: str = "data/analysis_results",
        enable_gemini: bool = True,
        gemini_interval_seconds: int = 30,
        save_frames: bool = True,
        frame_width: int = 1280,
        frame_height: int = 720
    ):
        """
        Initialize analysis runner

        Args:
            video_source: YouTube URL or video file path
            output_dir: Directory to save analysis results
            enable_gemini: Whether to run Gemini AI analysis
            gemini_interval_seconds: Interval between Gemini analyses
            save_frames: Whether to save annotated frames
            frame_width: Frame width for processing
            frame_height: Frame height for processing
        """
        self.video_source = video_source
        self.output_dir = output_dir
        self.enable_gemini = enable_gemini
        self.gemini_interval = gemini_interval_seconds
        self.save_frames = save_frames
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # Check if source is YouTube URL
        self.is_youtube = isinstance(video_source, str) and ('youtube.com' in video_source or 'youtu.be' in video_source)

        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/frames", exist_ok=True)
        os.makedirs(f"{output_dir}/clips", exist_ok=True)
        os.makedirs(f"{output_dir}/heatmaps", exist_ok=True)
        os.makedirs(f"{output_dir}/reports", exist_ok=True)

        # Initialize database
        init_db()
        self.db = SessionLocal()

        # Initialize detection components
        print("Initializing detection components...")
        self.camera = CameraManager(camera_source=video_source)
        self.person_detector = PersonDetector(confidence_threshold=0.7)
        self.face_detector = FaceDetector(tolerance=0.4)
        self.face_detector.load_known_faces_from_db(self.db)
        self.body_tracker = BodyTracker(iou_threshold=0.3, max_age=30)

        # Initialize Gemini analyzer if enabled
        self.gemini_analyzer = None
        if enable_gemini:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                self.gemini_analyzer = GeminiAnalyzer(api_key=api_key)
                print("Gemini AI analyzer initialized")
            else:
                print("Warning: GEMINI_API_KEY not found, Gemini analysis disabled")
                self.enable_gemini = False

        # Initialize retail analytics components
        print("Initializing retail analytics components...")
        self.trajectory_tracker = TrajectoryTracker(history_duration_seconds=60)
        self.dwell_calculator = DwellTimeCalculator()
        self.zone_detector = ZoneDetector()
        self.zone_detector.load_zones(self.db)
        self.occupancy_counter = OccupancyCounter()
        self.occupancy_counter.zone_detector = self.zone_detector
        self.line_crossing_detector = LineCrossingDetector()
        self.line_crossing_detector.load_lines(self.db)
        self.heatmap_generator = HeatmapGenerator(
            width=frame_width,
            height=frame_height,
            resolution=20
        )
        self.queue_detector = QueueDetector()

        # Tracking state
        self.active_persons: Dict[int, Dict] = {}  # person_id -> data
        self.frame_count = 0
        self.start_time = None
        self.last_gemini_time = None

        print("Analysis runner initialized successfully!")

    def generate_zones_from_video(self):
        """
        Pre-analysis phase: Capture initial video and generate zones using Gemini AI
        """
        if not self.enable_gemini or not self.gemini_analyzer:
            print("Gemini not enabled, loading default zones...")
            self.zone_detector.load_zones(self.db)
            self.line_crossing_detector.load_lines(self.db)
            return

        print("\n" + "="*60)
        print("PHASE 1: AI-POWERED ZONE GENERATION")
        print("="*60)

        try:
            # For YouTube URLs, pass directly to Gemini without downloading
            if self.is_youtube:
                print(f"Using YouTube URL directly for layout analysis: {self.video_source}")
                zone_config = self.gemini_analyzer.analyze_layout_and_generate_zones(
                    video_path=None,
                    youtube_url=self.video_source
                )
            else:
                # For local files, record 5-second clip for layout analysis
                print("Capturing initial video for layout analysis...")
                initial_clip = self.camera.record_clip(duration=5)
                
                if not initial_clip or not os.path.exists(initial_clip):
                    print("Warning: Failed to capture initial clip, using default zones")
                    self.zone_detector.load_zones(self.db)
                    self.line_crossing_detector.load_lines(self.db)
                    return

                print(f"Initial clip captured: {initial_clip}")
                print("Sending to Gemini AI for layout analysis...")
                zone_config = self.gemini_analyzer.analyze_layout_and_generate_zones(initial_clip)

            if "error" in zone_config:
                print(f"Error in Gemini layout analysis: {zone_config['error']}")
                print("Falling back to default zones")
                self.zone_detector.load_zones(self.db)
                self.line_crossing_detector.load_lines(self.db)
                return

            # Save zones to database
            from app.core.database import Zone, VirtualLine
            
            zones_created = 0
            lines_created = 0

            # Create zones
            for zone_data in zone_config.get("zones", []):
                try:
                    zone = Zone(
                        name=zone_data["name"],
                        zone_type=zone_data["zone_type"],
                        polygon_points=zone_data["polygon_points"],
                        color=zone_data.get("color", "#00FF00"),
                        max_capacity=zone_data.get("max_capacity")
                    )
                    self.db.add(zone)
                    zones_created += 1
                except Exception as e:
                    print(f"Error creating zone '{zone_data.get('name')}': {e}")

            # Create virtual lines
            for line_data in zone_config.get("virtual_lines", []):
                try:
                    line = VirtualLine(
                        name=line_data["name"],
                        start_point=line_data["start_point"],
                        end_point=line_data["end_point"],
                        count_direction=line_data.get("count_direction", "both"),
                        color=line_data.get("color", "#FF0000")
                    )
                    self.db.add(line)
                    lines_created += 1
                except Exception as e:
                    print(f"Error creating virtual line '{line_data.get('name')}': {e}")

            self.db.commit()

            print(f"\n✓ AI-Generated Configuration:")
            print(f"  - Zones created: {zones_created}")
            print(f"  - Virtual lines created: {lines_created}")

            # Reload zones and lines into detectors
            self.zone_detector.load_zones(self.db)
            self.line_crossing_detector.load_lines(self.db)

            print("\nZone generation complete!")
            print("="*60 + "\n")

        except Exception as e:
            print(f"Error during zone generation: {e}")
            print("Falling back to default zones")
            self.zone_detector.load_zones(self.db)
            self.line_crossing_detector.load_lines(self.db)

    def run_analysis(self, duration_seconds: Optional[int] = None, max_frames: Optional[int] = None):
        """
        Run comprehensive analysis

        Args:
            duration_seconds: Maximum duration to analyze (None = entire video)
            max_frames: Maximum frames to process (None = all frames)
        """
        print(f"\n{'='*60}")
        print(f"Starting Comprehensive Video Analysis")
        print(f"Video Source: {self.video_source}")
        print(f"Output Directory: {self.output_dir}")
        print(f"{'='*60}\n")

        self.start_time = datetime.utcnow()
        last_save_time = self.start_time
        last_heatmap_save = self.start_time

        try:
            # Start camera
            self.camera.start()
            print("Camera stream started")

            # PHASE 1: Generate zones from video using Gemini AI
            self.generate_zones_from_video()

            # PHASE 2: Main analysis loop
            print("\n" + "="*60)
            print("PHASE 2: COMPREHENSIVE VIDEO ANALYSIS")
            print("="*60 + "\n")

            while True:
                # Check termination conditions
                if max_frames and self.frame_count >= max_frames:
                    print(f"\nReached max frames ({max_frames})")
                    break

                if duration_seconds:
                    elapsed = (datetime.utcnow() - self.start_time).total_seconds()
                    if elapsed >= duration_seconds:
                        print(f"\nReached duration limit ({duration_seconds}s)")
                        break

                # Get frame
                frame = self.camera.get_current_frame()
                if frame is None:
                    print("No frame available, ending analysis")
                    break

                # Resize frame if needed
                if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))

                # Process frame
                current_time = datetime.utcnow()
                self.process_frame(frame, current_time)

                self.frame_count += 1

                # Progress update
                if self.frame_count % 30 == 0:
                    elapsed = (current_time - self.start_time).total_seconds()
                    fps = self.frame_count / elapsed if elapsed > 0 else 0
                    print(f"Processed {self.frame_count} frames ({fps:.1f} fps) | "
                          f"Active persons: {len(self.active_persons)}")

                # Save data periodically (every 10 seconds)
                if (current_time - last_save_time).total_seconds() >= 10:
                    self.save_periodic_data(current_time)
                    last_save_time = current_time

                # Save heatmap periodically (every 60 seconds)
                if (current_time - last_heatmap_save).total_seconds() >= 60:
                    self.save_heatmap(current_time)
                    last_heatmap_save = current_time

                # Run Gemini analysis periodically
                if self.enable_gemini and self.gemini_analyzer:
                    if self.last_gemini_time is None or \
                       (current_time - self.last_gemini_time).total_seconds() >= self.gemini_interval:
                        self.run_gemini_analysis(current_time)
                        self.last_gemini_time = current_time

        except KeyboardInterrupt:
            print("\n\nAnalysis interrupted by user")
        except Exception as e:
            print(f"\nError during analysis: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.finalize_analysis()

    def process_frame(self, frame: np.ndarray, timestamp: datetime):
        """Process a single frame with all analysis components"""

        # Step 1: Detect persons (bodies)
        person_detections = self.person_detector.detect_persons(frame)

        if len(person_detections) == 0:
            return

        # Step 2: Prepare detections for body tracker (bbox, confidence, person_id)
        # We'll try to recognize faces first, then update tracker
        detections_with_person_ids = []

        for person_bbox, person_confidence in person_detections:
            # Extract person ROI
            roi_frame, offset_xy = self.person_detector.extract_person_roi(
                frame, person_bbox, padding=10
            )

            # Detect faces in person ROI
            detected_faces = self.face_detector.detect_faces_in_roi(
                frame, person_bbox, offset_xy
            )

            # Check for visible faces
            person_id = None
            visible_faces = []
            for detection_result in detected_faces:
                try:
                    if len(detection_result) == 3:
                        face_encoding, face_location, face_confidence = detection_result
                        if self.person_detector.is_face_visible(
                            person_bbox, face_location, face_confidence
                        ):
                            visible_faces.append((face_encoding, face_location))
                except Exception as e:
                    continue

            # Try to recognize face if visible
            if len(visible_faces) > 0:
                best_face_encoding, best_face_location = visible_faces[0]
                person_id = self.face_detector.recognize_face(best_face_encoding)

                if person_id:
                    # Known person
                    person = self.db.query(Person).filter(Person.id == person_id).first()
                    self.face_detector.update_person_visit(self.db, person_id)
                else:
                    # Unknown person - add to database
                    person = self.face_detector.add_person_to_db(
                        self.db, best_face_encoding, frame, best_face_location
                    )
                    person_id = person.id

                # Log face detection event
                frame_path = None
                if self.save_frames and self.frame_count % 30 == 0:
                    frame_path = self.save_annotated_frame(frame, person_bbox, person_id)

                self.face_detector.log_detection_event(
                    self.db, person_id, person_confidence, frame_path
                )

            detections_with_person_ids.append((person_bbox, person_confidence, person_id))

        # Step 3: Update body tracker with all detections
        tracked_bodies = self.body_tracker.update(detections_with_person_ids, timestamp)

        # Step 4: Process each tracked body
        current_positions = {}

        for track_data in tracked_bodies:
            tracking_id = track_data['tracking_id']
            person_bbox = track_data['bbox']
            person_confidence = track_data['confidence']
            person_id = track_data['person_id']

            # Calculate position (centroid)
            left, top, right, bottom = person_bbox
            norm_x = ((left + right) / 2) / self.frame_width
            norm_y = ((top + bottom) / 2) / self.frame_height

            # Detect current zone
            current_zone = self.zone_detector.find_zone((norm_x, norm_y))
            zone_id = current_zone.get('id') if current_zone else None

            # Log body detection to database
            self.body_tracker.log_detection_to_db(
                self.db,
                tracking_id=tracking_id,
                bbox=person_bbox,
                confidence=person_confidence,
                person_id=person_id,
                zone_id=zone_id,
                frame_path=None
            )

            # Update/create person session
            self.body_tracker.update_or_create_session(
                self.db,
                tracking_id=tracking_id,
                person_id=person_id,
                zone_id=zone_id
            )

            # Store position for this frame (use tracking_id as key)
            current_positions[tracking_id] = (norm_x, norm_y)

            # Update trajectory (now works with tracking_id)
            self.trajectory_tracker.update_position(
                tracking_id, person_id, person_bbox, timestamp,
                self.frame_width, self.frame_height, zone_id
            )

            # Update dwell time (now works with tracking_id)
            dwell_time = self.dwell_calculator.update(
                tracking_id, person_id, zone_id, (norm_x, norm_y), timestamp
            )

            # Check line crossings (now works with tracking_id)
            crossing_event = self.line_crossing_detector.check_crossing(
                tracking_id, person_id, (norm_x, norm_y), timestamp
            )
            if crossing_event:
                self.line_crossing_detector.log_crossing(
                    self.db, crossing_event, timestamp
                )

            # Add to heatmap (always, regardless of person_id)
            self.heatmap_generator.add_detection((norm_x, norm_y), weight=1.0)

            # Track active body (use tracking_id)
            self.active_persons[tracking_id] = {
                'tracking_id': tracking_id,
                'person_id': person_id,
                'last_seen': timestamp,
                'position': (norm_x, norm_y),
                'bbox': person_bbox,
                'zone': current_zone
            }

        # Update occupancy
        occupancy_counts = self.occupancy_counter.update(current_positions, timestamp)

        # Detect queues
        queues = self.queue_detector.detect_queues(current_positions, self.zone_detector)
        for queue in queues:
            self.queue_detector.log_queue_metrics(self.db, queue, timestamp)

        # Clean up persons not seen recently
        self.cleanup_inactive_persons(timestamp)

    def save_annotated_frame(self, frame: np.ndarray, bbox: Tuple, person_id: int) -> str:
        """Save frame with annotations"""
        annotated_frame = frame.copy()
        
        # Draw person box
        left, top, right, bottom = bbox
        cv2.rectangle(annotated_frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Add label
        label = f"Person ID: {person_id}"
        cv2.putText(annotated_frame, label, (left, top - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.output_dir}/frames/frame_{timestamp}_person_{person_id}.jpg"
        cv2.imwrite(filename, annotated_frame)
        
        return filename

    def run_gemini_analysis(self, timestamp: datetime):
        """Run comprehensive structured Gemini AI analysis on recent footage"""
        if not self.enable_gemini or not self.gemini_analyzer:
            return

        try:
            print(f"\n[{timestamp.strftime('%H:%M:%S')}] Running comprehensive Gemini AI analysis...")

            # Prepare detected bodies information for Gemini
            detected_bodies = []
            zones_info = []

            # Get info about all currently tracked bodies
            for tracking_id, body_data in self.active_persons.items():
                zone_name = body_data.get('zone', {}).get('name', 'Unknown') if body_data.get('zone') else 'Unknown'
                detected_bodies.append({
                    'tracking_id': tracking_id,
                    'person_id': body_data.get('person_id'),
                    'bbox': body_data.get('bbox'),
                    'zone': zone_name
                })

            # Get zones information
            if hasattr(self.zone_detector, 'zones'):
                zones_info = [
                    {
                        'name': zone.get('name', 'Unknown'),
                        'type': zone.get('zone_type', zone.get('type', 'unknown')),
                        'id': zone.get('id')
                    }
                    for zone in self.zone_detector.zones
                ]

            # Prepare product interaction context
            product_interactions = []
            if hasattr(self, 'interaction_tracker'):
                active_interactions = self.interaction_tracker.get_active_interactions()
                for interaction in active_interactions:
                    product_interactions.append({
                        'tracking_id': interaction.get('tracking_id'),
                        'product_name': interaction.get('product_name', 'Unknown Product'),
                        'interaction_type': interaction.get('interaction_type', 'examining'),
                        'hand_gesture': interaction.get('gesture_type'),
                        'duration': (datetime.utcnow() - interaction.get('start_time')).total_seconds() if interaction.get('start_time') else 0
                    })

            # Prepare gaze fixation context
            gaze_fixations = []
            if hasattr(self, 'gaze_detector') and hasattr(self.gaze_detector, 'active_fixations'):
                for tracking_id, fixation in self.gaze_detector.active_fixations.items():
                    gaze_fixations.append({
                        'tracking_id': tracking_id,
                        'target_zone': fixation.get('target_zone'),
                        'target_product': fixation.get('target_product'),
                        'duration': fixation.get('fixation_duration_seconds', 0)
                    })

            # Prepare queue status
            queue_status = None
            if hasattr(self, 'queue_detector'):
                active_queues = self.queue_detector.get_active_queues() if hasattr(self.queue_detector, 'get_active_queues') else []
                if active_queues:
                    queue_status = {
                        'queue_count': len(active_queues),
                        'max_length': max([q.get('length', 0) for q in active_queues]) if active_queues else 0,
                        'avg_wait_time': sum([q.get('avg_wait_time', 0) for q in active_queues]) / len(active_queues) if active_queues else 0
                    }

            # Prepare customer profile context (placeholder for future enhancement)
            customer_profiles = []
            # TODO: If customer recognition is enabled, populate this with recognized customer data

            # For YouTube URLs, pass directly to Gemini without downloading
            if self.is_youtube:
                print(f"Analyzing YouTube URL with {len(detected_bodies)} tracked bodies, {len(product_interactions)} product interactions, {len(gaze_fixations)} gaze fixations")
                result = self.gemini_analyzer.analyze_comprehensive_structured(
                    youtube_url=self.video_source,
                    detected_bodies=detected_bodies,
                    zones=zones_info,
                    product_interactions=product_interactions,
                    gaze_fixations=gaze_fixations,
                    queue_status=queue_status,
                    customer_profiles=customer_profiles,
                    time_window_seconds=10
                )
                clip_path = None
            else:
                # For local files, record 10-second clip
                clip_path = self.camera.record_clip(duration=10)

                if not clip_path or not os.path.exists(clip_path):
                    print("Failed to record clip for Gemini analysis")
                    return

                print(f"Analyzing video clip with {len(detected_bodies)} tracked bodies, {len(product_interactions)} product interactions, {len(gaze_fixations)} gaze fixations")
                result = self.gemini_analyzer.analyze_comprehensive_structured(
                    video_path=clip_path,
                    detected_bodies=detected_bodies,
                    zones=zones_info,
                    product_interactions=product_interactions,
                    gaze_fixations=gaze_fixations,
                    queue_status=queue_status,
                    customer_profiles=customer_profiles,
                    time_window_seconds=10
                )

            if result.get('success'):
                print("✅ Gemini comprehensive analysis completed successfully")

                # Save structured analysis to database
                scene_analysis = self.gemini_analyzer.save_comprehensive_analysis_to_db(
                    self.db,
                    result,
                    clip_path
                )

                if scene_analysis:
                    print(f"   Saved Scene Analysis ID: {scene_analysis.id}")

                    # Also save full JSON to file for reference
                    analysis_file = f"{self.output_dir}/reports/gemini_comprehensive_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
                    with open(analysis_file, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(result['structured_analysis'], f, indent=2, ensure_ascii=False)
                    print(f"   Analysis JSON saved to {analysis_file}")

                    # Print summary
                    structured = result['structured_analysis']
                    scene = structured.get('scene', {})
                    individuals = structured.get('individuals', [])
                    events = structured.get('events', [])
                    alerts = structured.get('alerts', [])

                    print(f"\n   📊 Analysis Summary:")
                    print(f"      Scene: {scene.get('overall_summary', 'N/A')[:80]}...")
                    print(f"      Individuals analyzed: {len(individuals)}")
                    print(f"      Events detected: {len(events)}")
                    print(f"      Alerts generated: {len(alerts)}")

            else:
                print(f"❌ Gemini analysis error: {result.get('error')}")
                if result.get('raw_response'):
                    print(f"   Raw response (first 500 chars): {result['raw_response'][:500]}...")

        except Exception as e:
            print(f"Error running comprehensive Gemini analysis: {e}")
            import traceback
            traceback.print_exc()

    def save_periodic_data(self, timestamp: datetime):
        """Save data periodically"""
        try:
            # Save trajectories
            for person_id in self.active_persons.keys():
                self.trajectory_tracker.save_to_db(self.db, person_id)

            # Log occupancy
            self.occupancy_counter.log_to_db(self.db, timestamp)

        except Exception as e:
            print(f"Error saving periodic data: {e}")

    def save_heatmap(self, timestamp: datetime):
        """Save heatmap"""
        try:
            # Generate heatmap image
            heatmap_overlay = self.heatmap_generator.generate_heatmap_overlay(alpha=0.6)
            
            # Save image
            time_bucket = timestamp.strftime("%Y%m%d_%H")
            heatmap_file = f"{self.output_dir}/heatmaps/heatmap_{time_bucket}.png"
            cv2.imwrite(heatmap_file, heatmap_overlay)
            
            # Save to database
            self.heatmap_generator.save_to_db(self.db, time_bucket)
            
            print(f"Heatmap saved: {heatmap_file}")

        except Exception as e:
            print(f"Error saving heatmap: {e}")

    def cleanup_inactive_persons(self, current_time: datetime, timeout_seconds: int = 5):
        """Remove bodies not seen recently"""
        inactive_tracking_ids = []

        for tracking_id, data in self.active_persons.items():
            time_since_seen = (current_time - data['last_seen']).total_seconds()

            if time_since_seen > timeout_seconds:
                inactive_tracking_ids.append(tracking_id)

                # End person session in database
                self.body_tracker.end_session(self.db, tracking_id)

                # Log zone exit if in a zone (now uses tracking_id)
                zone = data.get('zone')
                if zone and zone.get('id'):
                    self.dwell_calculator.exit_zone(
                        self.db, tracking_id, zone['id'], current_time
                    )

                # End trajectory tracking (now uses tracking_id)
                self.trajectory_tracker.end_session(tracking_id)

        for tracking_id in inactive_tracking_ids:
            del self.active_persons[tracking_id]

    def finalize_analysis(self):
        """Finalize analysis and generate summary"""
        print("\n" + "="*60)
        print("Finalizing Analysis")
        print("="*60)

        try:
            # Stop camera
            self.camera.stop()

            # Save final heatmap
            final_time = datetime.utcnow()
            self.save_heatmap(final_time)

            # Save final trajectories
            for person_id in self.active_persons.keys():
                self.trajectory_tracker.save_to_db(self.db, person_id)

            # Generate summary report
            self.generate_summary_report()

            # Close database
            self.db.close()

            print("\nAnalysis completed successfully!")
            print(f"Results saved to: {self.output_dir}")

        except Exception as e:
            print(f"Error during finalization: {e}")

    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        try:
            elapsed_time = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Get statistics from database
            total_persons = self.db.query(Person).count()
            total_detections = self.db.query(DetectionEvent).count()
            
            report_lines = [
                "="*60,
                "VIDEO ANALYSIS SUMMARY REPORT",
                "="*60,
                f"\nAnalysis Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Analysis Duration: {elapsed_time:.1f} seconds",
                f"Total Frames Processed: {self.frame_count}",
                f"Average FPS: {self.frame_count / elapsed_time:.2f}" if elapsed_time > 0 else "Average FPS: 0",
                f"\nVideo Source: {self.video_source}",
                f"Output Directory: {self.output_dir}",
                f"\n{'='*60}",
                f"\nDETECTION STATISTICS",
                f"{'='*60}",
                f"Total Unique Persons: {total_persons}",
                f"Total Detection Events: {total_detections}",
                f"\nActive Analysis Components:",
                f"  - Person Detection: ✓",
                f"  - Face Recognition: ✓",
                f"  - Trajectory Tracking: ✓",
                f"  - Dwell Time Analysis: ✓",
                f"  - Zone Detection: ✓",
                f"  - Line Crossing Detection: ✓",
                f"  - Occupancy Tracking: ✓",
                f"  - Heatmap Generation: ✓",
                f"  - Queue Detection: ✓",
                f"  - Gemini AI Analysis: {'✓' if self.enable_gemini else '✗'}",
                f"\n{'='*60}",
            ]
            
            # Write report with UTF-8 encoding to handle special characters
            report_file = f"{self.output_dir}/reports/analysis_summary.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            print('\n'.join(report_lines))
            print(f"\nSummary report saved to: {report_file}")

        except Exception as e:
            print(f"Error generating summary report: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Video Analysis Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze YouTube video for 60 seconds
  python analysis_runner.py --source "https://www.youtube.com/watch?v=KMJS66jBtVQ" --duration 60

  # Analyze local video file with Gemini analysis every 30 seconds
  python analysis_runner.py --source /path/to/video.mp4 --gemini-interval 30

  # Process max 1000 frames without Gemini
  python analysis_runner.py --source video.mp4 --max-frames 1000 --no-gemini
        """
    )
    
    parser.add_argument('--source', required=True,
                       help='Video source (YouTube URL or local file path)')
    parser.add_argument('--output', default='data/analysis_results',
                       help='Output directory for results (default: data/analysis_results)')
    parser.add_argument('--duration', type=int, default=None,
                       help='Maximum analysis duration in seconds (default: entire video)')
    parser.add_argument('--max-frames', type=int, default=None,
                       help='Maximum frames to process (default: all frames)')
    parser.add_argument('--no-gemini', action='store_true',
                       help='Disable Gemini AI analysis')
    parser.add_argument('--gemini-interval', type=int, default=30,
                       help='Interval between Gemini analyses in seconds (default: 30)')
    parser.add_argument('--no-save-frames', action='store_true',
                       help='Disable saving annotated frames')
    parser.add_argument('--width', type=int, default=1280,
                       help='Frame width for processing (default: 1280)')
    parser.add_argument('--height', type=int, default=720,
                       help='Frame height for processing (default: 720)')

    args = parser.parse_args()

    # Initialize runner
    runner = ComprehensiveAnalysisRunner(
        video_source=args.source,
        output_dir=args.output,
        enable_gemini=not args.no_gemini,
        gemini_interval_seconds=args.gemini_interval,
        save_frames=not args.no_save_frames,
        frame_width=args.width,
        frame_height=args.height
    )

    # Run analysis
    runner.run_analysis(
        duration_seconds=args.duration,
        max_frames=args.max_frames
    )


if __name__ == "__main__":
    main()
