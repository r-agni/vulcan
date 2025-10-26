from google import genai
from google.genai import types
import os
import json
import re
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import BehaviorAnalysis, SceneAnalysis, EventLog, InteractionLog
import cv2


class GeminiAnalyzer:
    """Use Gemini API for video and behavior analysis"""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def analyze_behavior(
        self, 
        video_path: str = None, 
        youtube_url: str = None,
        start_offset: str = None,
        end_offset: str = None
    ) -> Dict[str, str]:
        """
        Analyze person behavior from video clip
        
        Args:
            video_path: Path to local video file
            youtube_url: YouTube URL (preferred for faster processing)
            start_offset: Start time for clipping (e.g., '10s', '1m30s')
            end_offset: End time for clipping (e.g., '45s', '2m15s')
            
        Returns:
            Dictionary with detailed analysis of behavior, clothing, emotions, pathway, and interests
        """
        try:
            import time
            
            # Prepare video input - prefer YouTube URL if available
            video_metadata = None
            if start_offset or end_offset:
                video_metadata = types.VideoMetadata(
                    start_offset=start_offset,
                    end_offset=end_offset
                )
            
            if youtube_url:
                print(f"Analyzing YouTube URL: {youtube_url}")
                video_part = types.Part(
                    file_data=types.FileData(file_uri=youtube_url),
                    video_metadata=video_metadata
                )
            elif video_path:
                # Upload video file
                print(f"Uploading video file: {video_path}")
                video_file = self.client.files.upload(file=video_path)
                
                # Wait for file to become active
                max_retries = 10
                for retry in range(max_retries):
                    file_status = self.client.files.get(name=video_file.name)
                    if file_status.state.name == "ACTIVE":
                        break
                    if retry < max_retries - 1:
                        time.sleep(2)
                
                if video_metadata:
                    video_part = types.Part(
                        file_data=types.FileData(file_uri=video_file.uri),
                        video_metadata=video_metadata
                    )
                else:
                    video_part = video_file
            else:
                return {"error": "Must provide either video_path or youtube_url"}

            # Create comprehensive analysis prompt
            prompt = """
            Analyze this surveillance video footage and provide a detailed report:

            1. PERSON DESCRIPTION:
               - Physical appearance and clothing details
               - Age estimate and gender
               - Distinctive features

            2. EMOTIONAL STATE:
               - Facial expressions and body language
               - Mood indicators
               - Confidence level

            3. MOVEMENT PATTERNS:
               - Walking pathway and direction
               - Speed and gait
               - Points where person stops or lingers

            4. AREAS OF INTEREST:
               - Products or areas the person looks at
               - Items picked up or examined
               - Duration of attention to specific areas

            5. ACTIONS:
               - What the person is doing
               - Interactions with objects or environment
               - Any unusual or noteworthy behaviors

            6. TIMESTAMPS:
               - Key moments in the video with timestamps (MM:SS format)

            Provide specific details and be objective in your analysis.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_part, prompt]
            )

            return {
                "full_analysis": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error analyzing video: {e}")
            return {"error": str(e)}

    def analyze_single_frame(self, frame_path: str) -> Dict[str, str]:
        """
        Analyze a single frame for quick assessment
        """
        try:
            # Read frame as bytes
            with open(frame_path, 'rb') as f:
                frame_bytes = f.read()

            prompt = """
            Analyze this surveillance camera frame:
            - Describe the person's clothing and appearance
            - Identify their emotional state from facial expression
            - Note any objects they're carrying
            - Describe their posture and body language

            Be concise but specific.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(data=frame_bytes, mime_type='image/jpeg')
                        ),
                        types.Part(text=prompt)
                    ]
                )
            )

            return {
                "frame_analysis": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error analyzing frame: {e}")
            return {"error": str(e)}

    def analyze_with_custom_fps(
        self, 
        video_path: str = None,
        youtube_url: str = None,
        fps: int = 2
    ) -> Dict[str, str]:
        """
        Analyze video with custom frame sampling rate
        Higher FPS for detailed action analysis
        
        Args:
            video_path: Path to local video file (<20MB)
            youtube_url: YouTube URL (alternative to video_path)
            fps: Frames per second to sample (default: 2, use <1 for long videos)
        """
        try:
            prompt = """
            Analyze this video clip with focus on detailed movements and actions:
            - Track the person's exact pathway
            - Note every interaction or point of interest
            - Identify products or areas examined
            - Provide timestamps for key actions

            Be very detailed in your analysis.
            """
            
            if youtube_url:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=types.Content(
                        parts=[
                            types.Part(
                                file_data=types.FileData(file_uri=youtube_url),
                                video_metadata=types.VideoMetadata(fps=fps)
                            ),
                            types.Part(text=prompt)
                        ]
                    )
                )
            elif video_path:
                with open(video_path, 'rb') as f:
                    video_bytes = f.read()

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=types.Content(
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    data=video_bytes,
                                    mime_type='video/mp4'
                                ),
                                video_metadata=types.VideoMetadata(fps=fps)
                            ),
                            types.Part(text=prompt)
                        ]
                    )
                )
            else:
                return {"error": "Must provide either video_path or youtube_url"}

            return {
                "detailed_analysis": response.text,
                "fps_used": fps,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error in detailed analysis: {e}")
            return {"error": str(e)}

    def compare_clips(self, clip1_path: str, clip2_path: str) -> Dict[str, str]:
        """
        Compare two video clips (e.g., inside and outside camera)
        """
        try:
            file1 = self.client.files.upload(file=clip1_path)
            file2 = self.client.files.upload(file=clip2_path)

            prompt = """
            Compare these two video clips from different camera angles:
            - Is it the same person? How confident are you?
            - Describe consistent features (clothing, gait, items carried)
            - Note any differences in behavior between the two clips
            - Track the person's overall journey
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[file1, file2, prompt]
            )

            return {
                "comparison": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error comparing clips: {e}")
            return {"error": str(e)}

    def save_analysis_to_db(
        self,
        db: Session,
        person_id: Optional[int],
        detection_event_id: int,
        analysis_type: str,
        analysis_text: str,
        video_clip_path: Optional[str] = None
    ) -> BehaviorAnalysis:
        """Save behavior analysis to database"""
        analysis = BehaviorAnalysis(
            person_id=person_id,
            detection_event_id=detection_event_id,
            analysis_type=analysis_type,
            analysis_text=analysis_text,
            video_clip_path=video_clip_path,
            timestamp=datetime.utcnow()
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    def stream_analysis(self, video_path: str) -> str:
        """
        Stream real-time analysis (for live dashboard updates)
        Returns analysis text that can be sent via websocket
        """
        analysis = self.analyze_behavior(video_path)
        return analysis.get("full_analysis", "Analysis in progress...")

    # ==================== RETAIL-SPECIFIC ANALYSIS ====================

    def analyze_shopping_behavior(self, video_path: str) -> Dict[str, str]:
        """Analyze shopping behavior and purchase intent"""
        try:
            import time
            
            # Upload video file
            video_file = self.client.files.upload(file=video_path)
            
            # Wait for file to become active (Gemini API requirement)
            max_retries = 10
            for retry in range(max_retries):
                file_status = self.client.files.get(name=video_file.name)
                if file_status.state.name == "ACTIVE":
                    break
                if retry < max_retries - 1:
                    time.sleep(2)
            
            prompt = """
            Analyze this retail store customer behavior:

            SHOPPING BEHAVIOR:
            - Which product displays/shelves is the customer examining?
            - How long do they spend at each location? (provide timestamps)
            - Do they pick up items? Put them back? Compare products?
            - Are they reading labels or checking prices?
            - Shopping alone or with companions?

            PURCHASE INTENT SIGNALS:
            - Rate purchase intent (0-10) for products examined
            - Signs of interest: prolonged attention, multiple examinations, comparing options
            - Signs of hesitation: putting items back, price checking, looking uncertain
            - Are they looking for store assistance?

            PATHWAY & ENGAGEMENT:
            - Is their shopping purposeful (direct to items) or browsing?
            - Do they backtrack to previous areas?
            - Which displays successfully catch their attention?
            - Navigation efficiency through the store

            EMOTIONAL INDICATORS:
            - Customer satisfaction/frustration levels
            - Confidence in product selections
            - Overall shopping experience sentiment

            Provide specific timestamps (MM:SS) for key moments and behaviors.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_file, prompt]
            )

            return {
                "shopping_analysis": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error in shopping analysis: {e}")
            return {"error": str(e)}

    def analyze_queue_experience(self, video_path: str) -> Dict[str, str]:
        """Analyze customer experience in queue/checkout"""
        try:
            video_file = self.client.files.upload(file=video_path)

            prompt = """
            Analyze customer queue/waiting experience:

            CUSTOMER EMOTIONAL STATE:
            - Patience level (calm, neutral, frustrated, anxious)
            - Body language indicators (fidgeting, checking time, looking around)
            - Facial expressions showing satisfaction/dissatisfaction

            QUEUE BEHAVIOR:
            - Is customer engaged (phone, conversation, waiting patiently)?
            - Queue abandonment risk level (1-10)
            - Interaction with other customers or staff

            WAIT TIME PERCEPTION:
            - Does queue appear to move steadily?
            - Customer reactions to queue length/wait
            - Suggested improvements for better experience

            SERVICE QUALITY:
            - Staff responsiveness visible?
            - Checkout efficiency observed

            Provide actionable insights for reducing wait frustration.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_file, prompt]
            )

            return {
                "queue_analysis": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error in queue analysis: {e}")
            return {"error": str(e)}

    def analyze_store_layout_effectiveness(self, video_path: str) -> Dict[str, str]:
        """Analyze store layout and customer navigation patterns"""
        try:
            video_file = self.client.files.upload(file=video_path)

            prompt = """
            Analyze store layout effectiveness from customer movement:

            NAVIGATION EFFICIENCY:
            - Can customers find what they're looking for easily?
            - Are there confusion points or dead-ends?
            - Path efficiency rating (1-10)

            TRAFFIC FLOW:
            - Identify congestion/bottleneck areas
            - Dead zones with minimal customer traffic
            - High-traffic popular areas

            DISPLAY EFFECTIVENESS:
            - Which displays attract customer attention?
            - Which displays are ignored or overlooked?
            - Optimal product placement suggestions

            SIGNAGE & WAYFINDING:
            - Are customers able to navigate without assistance?
            - Signs of confusion or searching behavior
            - Suggested improvements for better flow

            ACCESSIBILITY:
            - Any obstacles or navigation difficulties?
            - Customer-friendly layout rating

            Provide specific recommendations for layout optimization.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_file, prompt]
            )

            return {
                "layout_analysis": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error in layout analysis: {e}")
            return {"error": str(e)}

    def analyze_product_interaction(self, video_path: str, product_zone: str) -> Dict[str, str]:
        """Analyze customer interaction with specific product/display"""
        try:
            video_file = self.client.files.upload(file=video_path)

            prompt = f"""
            Analyze customer interaction with {product_zone} product area:

            ENGAGEMENT LEVEL:
            - Time spent examining products (with timestamps)
            - Number of items picked up/examined
            - Engagement intensity (casual glance vs. deep examination)

            INTERACTION DETAILS:
            - Which specific products attract most attention?
            - Customer actions: browsing, comparing, reading labels, testing
            - Items placed in basket vs. put back

            DECISION-MAKING PROCESS:
            - Signs of decision-making: comparing options, price checking
            - Factors influencing selection/rejection
            - Purchase likelihood (1-10)

            DISPLAY EFFECTIVENESS:
            - Is the product display/arrangement effective?
            - Customer ease of access and examination
            - Suggested improvements for better conversion

            Provide insights to optimize product presentation and increase engagement.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_file, prompt]
            )

            return {
                "product_interaction_analysis": response.text,
                "product_zone": product_zone,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error in product interaction analysis: {e}")
            return {"error": str(e)}

    def transcribe_with_visual_descriptions(
        self,
        video_path: str = None,
        youtube_url: str = None,
        start_offset: str = None,
        end_offset: str = None
    ) -> Dict[str, str]:
        """
        Transcribe audio and provide visual descriptions of video content
        
        Args:
            video_path: Path to local video file
            youtube_url: YouTube URL (preferred for faster processing)
            start_offset: Start time for clipping (e.g., '10s', '1m30s')
            end_offset: End time for clipping (e.g., '45s', '2m15s')
            
        Returns:
            Dictionary with audio transcription and visual descriptions with timestamps
        """
        try:
            import time
            
            # Prepare video input - prefer YouTube URL if available
            video_metadata = None
            if start_offset or end_offset:
                video_metadata = types.VideoMetadata(
                    start_offset=start_offset,
                    end_offset=end_offset
                )
            
            if youtube_url:
                print(f"Transcribing YouTube URL: {youtube_url}")
                video_part = types.Part(
                    file_data=types.FileData(file_uri=youtube_url),
                    video_metadata=video_metadata
                )
            elif video_path:
                # Upload video file
                print(f"Uploading video file for transcription: {video_path}")
                video_file = self.client.files.upload(file=video_path)
                
                # Wait for file to become active
                max_retries = 10
                for retry in range(max_retries):
                    file_status = self.client.files.get(name=video_file.name)
                    if file_status.state.name == "ACTIVE":
                        break
                    if retry < max_retries - 1:
                        time.sleep(2)
                
                if video_metadata:
                    video_part = types.Part(
                        file_data=types.FileData(file_uri=video_file.uri),
                        video_metadata=video_metadata
                    )
                else:
                    video_part = video_file
            else:
                return {"error": "Must provide either video_path or youtube_url"}

            prompt = """
            Transcribe the audio from this video, giving timestamps for salient events in the video. 
            Also provide visual descriptions.
            
            Format your response as follows:
            
            AUDIO TRANSCRIPTION:
            [MM:SS] Speaker/Sound: [What was said or heard]
            
            VISUAL DESCRIPTIONS:
            [MM:SS] Visual: [What is happening visually at this moment]
            
            Provide detailed timestamps and descriptions for all significant events.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_part, prompt]
            )

            return {
                "transcription": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error transcribing video: {e}")
            return {"error": str(e)}

    def query_at_timestamp(
        self,
        video_path: str = None,
        youtube_url: str = None,
        timestamp: str = None,
        question: str = None
    ) -> Dict[str, str]:
        """
        Ask questions about specific points in time within the video
        
        Args:
            video_path: Path to local video file
            youtube_url: YouTube URL (preferred for faster processing)
            timestamp: Time to query (MM:SS format, e.g., '01:15')
            question: Question to ask about that timestamp
            
        Returns:
            Dictionary with answer to the question
        """
        try:
            import time
            
            if youtube_url:
                print(f"Querying YouTube URL at timestamp {timestamp}")
                video_part = types.Part(
                    file_data=types.FileData(file_uri=youtube_url)
                )
            elif video_path:
                # Upload video file
                print(f"Uploading video file for timestamp query: {video_path}")
                video_file = self.client.files.upload(file=video_path)
                
                # Wait for file to become active
                max_retries = 10
                for retry in range(max_retries):
                    file_status = self.client.files.get(name=video_file.name)
                    if file_status.state.name == "ACTIVE":
                        break
                    if retry < max_retries - 1:
                        time.sleep(2)
                
                video_part = video_file
            else:
                return {"error": "Must provide either video_path or youtube_url"}

            # Create prompt with timestamp reference
            if question:
                prompt = f"At timestamp {timestamp}, {question}"
            else:
                prompt = f"What is happening at timestamp {timestamp}? Provide a detailed description."

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_part, prompt]
            )

            return {
                "timestamp_query": timestamp,
                "question": question or "What is happening at this timestamp?",
                "answer": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error querying timestamp: {e}")
            return {"error": str(e)}

    def analyze_video_segment(
        self,
        video_path: str = None,
        youtube_url: str = None,
        start_offset: str = None,
        end_offset: str = None,
        fps: int = 1,
        custom_prompt: str = None
    ) -> Dict[str, str]:
        """
        Analyze a specific segment of video with custom parameters
        
        Args:
            video_path: Path to local video file (<20MB for inline)
            youtube_url: YouTube URL (alternative to video_path)
            start_offset: Start time for clipping (e.g., '10s', '1m30s')
            end_offset: End time for clipping (e.g., '45s', '2m15s')
            fps: Frames per second to sample (default: 1)
            custom_prompt: Custom analysis prompt
            
        Returns:
            Dictionary with segment analysis
        """
        try:
            import time
            
            # Default prompt if not provided
            if not custom_prompt:
                custom_prompt = """
                Analyze this video segment and provide:
                1. A summary of what happens
                2. Key actions and events with timestamps (MM:SS)
                3. Notable observations
                """
            
            # Prepare video metadata
            video_metadata = types.VideoMetadata(fps=fps)
            if start_offset:
                video_metadata.start_offset = start_offset
            if end_offset:
                video_metadata.end_offset = end_offset
            
            if youtube_url:
                print(f"Analyzing YouTube segment: {start_offset} to {end_offset}")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=types.Content(
                        parts=[
                            types.Part(
                                file_data=types.FileData(file_uri=youtube_url),
                                video_metadata=video_metadata
                            ),
                            types.Part(text=custom_prompt)
                        ]
                    )
                )
            elif video_path:
                file_size = os.path.getsize(video_path)
                
                # Use inline data for small files
                if file_size < 20 * 1024 * 1024:  # 20MB
                    print(f"Analyzing video segment inline: {start_offset} to {end_offset}")
                    with open(video_path, 'rb') as f:
                        video_bytes = f.read()
                    
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=types.Content(
                            parts=[
                                types.Part(
                                    inline_data=types.Blob(
                                        data=video_bytes,
                                        mime_type='video/mp4'
                                    ),
                                    video_metadata=video_metadata
                                ),
                                types.Part(text=custom_prompt)
                            ]
                        )
                    )
                else:
                    # Upload larger files
                    print(f"Uploading video file for segment analysis: {video_path}")
                    video_file = self.client.files.upload(file=video_path)
                    
                    # Wait for file to become active
                    max_retries = 10
                    for retry in range(max_retries):
                        file_status = self.client.files.get(name=video_file.name)
                        if file_status.state.name == "ACTIVE":
                            break
                        if retry < max_retries - 1:
                            time.sleep(2)
                    
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=types.Content(
                            parts=[
                                types.Part(
                                    file_data=types.FileData(file_uri=video_file.uri),
                                    video_metadata=video_metadata
                                ),
                                types.Part(text=custom_prompt)
                            ]
                        )
                    )
            else:
                return {"error": "Must provide either video_path or youtube_url"}

            return {
                "segment_analysis": response.text,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "fps": fps,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error analyzing video segment: {e}")
            return {"error": str(e)}

    # ==================== COMPREHENSIVE STRUCTURED ANALYSIS ====================

    def analyze_comprehensive_structured(
        self,
        video_path: str = None,
        youtube_url: str = None,
        detected_bodies: List[Dict] = None,
        zones: List[Dict] = None,
        product_interactions: List[Dict] = None,
        gaze_fixations: List[Dict] = None,
        queue_status: Dict = None,
        customer_profiles: List[Dict] = None,
        time_window_seconds: int = 10
    ) -> Dict:
        """
        Comprehensive structured analysis of video scene
        Returns nested JSON with scene-level, individual-level, and zone-level analysis

        Args:
            video_path: Path to local video file
            youtube_url: YouTube URL (preferred for faster processing)
            detected_bodies: List of detected bodies with tracking info
                            [{"tracking_id": "track_001", "bbox": [...], "person_id": 5, "zone": "Electronics"}]
            zones: List of zone definitions for context
            product_interactions: List of active product interactions
                                 [{"tracking_id": "track_001", "product_name": "Product X", "interaction_type": "examining", "hand_gesture": "pointing"}]
            gaze_fixations: List of active gaze fixations
                           [{"tracking_id": "track_001", "target_zone": "Electronics", "duration": 3.5}]
            queue_status: Current queue information
                         {"queue_count": 1, "max_length": 3, "avg_wait_time": 45.0}
            customer_profiles: List of recognized customer profiles
                              [{"tracking_id": "track_001", "profile_uuid": "xxx", "vip_status": true, "visit_frequency": "weekly"}]
            time_window_seconds: Duration of analysis window

        Returns:
            Structured dictionary with comprehensive analysis
        """
        try:
            import time

            # Prepare video input
            video_metadata = None
            if youtube_url:
                print(f"Analyzing YouTube URL: {youtube_url}")
                video_part = types.Part(
                    file_data=types.FileData(file_uri=youtube_url)
                )
            elif video_path:
                print(f"Uploading video file: {video_path}")
                video_file = self.client.files.upload(file=video_path)

                # Wait for file to become active
                max_retries = 10
                for retry in range(max_retries):
                    file_status = self.client.files.get(name=video_file.name)
                    if file_status.state.name == "ACTIVE":
                        break
                    if retry < max_retries - 1:
                        time.sleep(2)

                video_part = video_file
            else:
                return {"error": "Must provide either video_path or youtube_url"}

            # Build context about detected bodies
            body_context = ""
            if detected_bodies:
                body_context = "\n\nDETECTED INDIVIDUALS IN FRAME:\n"
                for body in detected_bodies:
                    tracking_id = body.get('tracking_id', 'unknown')
                    person_id = body.get('person_id')
                    zone = body.get('zone', 'unknown zone')
                    person_info = f"Person #{person_id}" if person_id else "Unknown person"
                    body_context += f"- Tracking ID: {tracking_id} ({person_info}) in {zone}\n"

            # Build context about zones
            zone_context = ""
            if zones:
                zone_context = "\n\nSTORE ZONES:\n"
                for zone in zones:
                    zone_name = zone.get('name', 'Unknown')
                    zone_type = zone.get('type', 'unknown')
                    zone_context += f"- {zone_name} ({zone_type})\n"

            # Build context about product interactions
            product_context = ""
            if product_interactions:
                product_context = "\n\nACTIVE PRODUCT INTERACTIONS:\n"
                for interaction in product_interactions:
                    tracking_id = interaction.get('tracking_id', 'unknown')
                    product_name = interaction.get('product_name', 'Unknown Product')
                    interaction_type = interaction.get('interaction_type', 'examining')
                    hand_gesture = interaction.get('hand_gesture', 'none')
                    duration = interaction.get('duration', 0)
                    product_context += f"- {tracking_id} is {interaction_type} '{product_name}' (gesture: {hand_gesture}, duration: {duration:.1f}s)\n"

            # Build context about gaze fixations
            gaze_context = ""
            if gaze_fixations:
                gaze_context = "\n\nGAZE TRACKING DATA:\n"
                for fixation in gaze_fixations:
                    tracking_id = fixation.get('tracking_id', 'unknown')
                    target_zone = fixation.get('target_zone', 'Unknown Zone')
                    target_product = fixation.get('target_product')
                    duration = fixation.get('duration', 0)
                    if target_product:
                        gaze_context += f"- {tracking_id} gazing at '{target_product}' in {target_zone} ({duration:.1f}s)\n"
                    else:
                        gaze_context += f"- {tracking_id} gazing at {target_zone} ({duration:.1f}s)\n"

            # Build context about queues
            queue_context = ""
            if queue_status:
                queue_count = queue_status.get('queue_count', 0)
                max_length = queue_status.get('max_length', 0)
                avg_wait = queue_status.get('avg_wait_time', 0)
                if queue_count > 0:
                    queue_context = f"\n\nQUEUE STATUS:\n- {queue_count} active queue(s), longest: {max_length} people, avg wait: {avg_wait:.0f}s\n"

            # Build context about customer profiles
            customer_context = ""
            if customer_profiles:
                customer_context = "\n\nCUSTOMER RECOGNITION:\n"
                for profile in customer_profiles:
                    tracking_id = profile.get('tracking_id', 'unknown')
                    vip = profile.get('vip_status', False)
                    frequency = profile.get('visit_frequency', 'unknown')
                    favorite_zones = profile.get('favorite_zones', [])
                    vip_badge = " (VIP)" if vip else ""
                    customer_context += f"- {tracking_id}: Returning customer{vip_badge}, visits {frequency}"
                    if favorite_zones:
                        customer_context += f", prefers {', '.join(favorite_zones[:2])}"
                    customer_context += "\n"

            # Create comprehensive structured prompt
            prompt = f"""
            Analyze this {time_window_seconds}-second surveillance video clip and provide a COMPREHENSIVE STRUCTURED ANALYSIS.

            {body_context}
            {zone_context}
            {product_context}
            {gaze_context}
            {queue_context}
            {customer_context}

            You MUST respond with VALID JSON in this EXACT structure (no additional text, no markdown):

            {{
              "analysis_timestamp": "2025-10-19T14:30:00Z",
              "time_window": {{"start": "00:00", "end": "00:{time_window_seconds:02d}"}},

              "scene": {{
                "overall_summary": "Detailed description of overall scene activity...",
                "crowd_density": "low|medium|high",
                "energy_level": "calm|moderate|busy|hectic",
                "dominant_activities": ["activity1", "activity2"],
                "environmental_context": "Description of environment, lighting, ambiance...",
                "anomalies_detected": []
              }},

              "events": [
                {{
                  "timestamp": "MM:SS",
                  "event_type": "customer_interaction|staff_interaction|queue_formation|product_pickup|movement|anomaly",
                  "severity": "normal|attention|warning|critical",
                  "description": "What happened",
                  "location": "Zone or area name",
                  "involved_tracking_ids": ["track_XXX"],
                  "requires_action": false,
                  "recommended_action": null
                }}
              ],

              "individuals": [
                {{
                  "body_tracking_id": "track_XXX",
                  "person_id": null,
                  "customer_profile_uuid": null,
                  "is_returning_customer": false,
                  "vip_status": false,
                  "appearance": {{
                    "clothing": "Detailed clothing description",
                    "accessories": "Items carried, worn",
                    "age_estimate": "XX-XX",
                    "gender_estimate": "male|female|unknown",
                    "distinctive_features": "Notable physical characteristics"
                  }},
                  "current_state": {{
                    "activity": "What they're doing",
                    "emotional_state": "Mood, demeanor",
                    "confidence_level": "Body language confidence",
                    "engagement_score": 0-10,
                    "purchase_intent_score": 0-10
                  }},
                  "location": {{
                    "current_zone": "Zone name",
                    "sub_location": "Specific area within zone",
                    "position_description": "Where exactly they are"
                  }},
                  "product_interactions": [
                    {{
                      "product_name": "Specific Product Name",
                      "product_category": "Electronics|Clothing|Food|etc",
                      "interaction_types": ["gazing", "reaching", "examining", "picking_up"],
                      "hand_gesture": "pointing|grabbing|holding|open_palm|null",
                      "hand_position": {{"x": 0.0, "y": 0.0}},
                      "gaze_duration_seconds": 0.0,
                      "interaction_duration_seconds": 0.0,
                      "engagement_level": 0-10,
                      "purchase_likelihood": 0-10,
                      "comparison_behavior": "comparing with other products|focused on single item|null"
                    }}
                  ],
                  "gaze_behavior": {{
                    "primary_focus_zone": "Zone name or null",
                    "secondary_focus_zones": ["Zone1", "Zone2"],
                    "attention_span_seconds": 0.0,
                    "distraction_level": "low|medium|high",
                    "visual_search_pattern": "systematic|random|targeted|null"
                  }},
                  "timeline_in_clip": [
                    {{"time": "MM:SS", "action": "What happened at this time"}}
                  ],
                  "interactions": [
                    {{
                      "type": "product|staff|customer|environment",
                      "item": "What they interacted with",
                      "duration": "Duration estimate",
                      "intensity": "low|medium|high"
                    }}
                  ],
                  "needs_assistance": true|false,
                  "recommended_action": "Action for staff to take, if any"
                }}
              ],

              "zones": {{
                "ZoneName": {{
                  "occupancy": 0,
                  "activity_level": "low|medium|high",
                  "dominant_behavior": "Primary activity",
                  "customer_engagement": "Description of engagement",
                  "staff_presence": true|false,
                  "recommended_action": "Suggestions for optimization"
                }}
              }},

              "interactions": [
                {{
                  "interaction_id": "int_XXX",
                  "type": "customer_product|customer_staff|customer_customer",
                  "participants": ["track_XXX", "track_YYY"],
                  "location": "Zone name",
                  "description": "What's happening",
                  "duration": "Estimate",
                  "outcome": "ongoing|positive|negative|neutral"
                }}
              ],

              "alerts": [
                {{
                  "alert_id": "alert_XXX",
                  "priority": "low|medium|high|critical",
                  "type": "sales_opportunity|queue_management|customer_service|security|product_interest|vip_customer",
                  "title": "Short alert title",
                  "message": "Detailed alert message",
                  "location": "Where",
                  "tracking_id": "track_XXX",
                  "product_name": "Product name if applicable",
                  "recommended_recipient": "sales_staff|manager|security",
                  "recommended_action": "Specific action to take",
                  "expiry_seconds": 300,
                  "context": {{
                    "customer_profile": "returning_customer|new_customer|vip|unknown",
                    "engagement_score": 0-10,
                    "time_in_zone_seconds": 0,
                    "similar_past_behavior": "description or null"
                  }}
                }}
              ],

              "metadata": {{
                "gemini_model": "gemini-2.5-flash",
                "confidence_score": 0.0-1.0,
                "frame_quality": "poor|fair|good|excellent",
                "lighting_conditions": "Description"
              }}
            }}

            IMPORTANT RULES:
            1. Return ONLY the JSON object, no markdown, no code blocks, no extra text
            2. Use the tracking IDs provided in the detected individuals list
            3. Be specific and detailed in all descriptions
            4. Include timestamps in MM:SS format for all events
            5. Provide actionable insights in recommended_action fields
            6. Score engagement and purchase intent objectively (0-10)
            7. Identify all visible interactions between people, products, staff
            8. Note any unusual behaviors or patterns
            9. Make zone-specific observations for each active zone
            10. Generate relevant alerts based on what you observe
            11. For product interactions: use ACTUAL product names from the product interaction context provided above
            12. For gaze behavior: correlate gaze tracking data with visible attention patterns in the video
            13. For customer recognition: use the customer profile information (VIP status, visit frequency) to inform your analysis
            14. For alerts: include tracking_id, product_name, and customer context when generating product-related or sales opportunity alerts
            15. Score purchase_likelihood based on combination of: gaze duration, hand gestures (grabbing/holding = high intent), interaction duration, and comparison behavior

            Begin your JSON response now:
            """

            # Call Gemini API
            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_part, prompt]
            )

            # Parse JSON response
            response_text = response.text.strip()

            # Try to extract JSON from response (remove markdown code blocks if present)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            elif response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text.strip('`').strip()
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()

            # Parse JSON
            structured_data = json.loads(response_text)

            return {
                "success": True,
                "structured_analysis": structured_data,
                "raw_response": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini JSON response: {e}")
            print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            return {
                "success": False,
                "error": f"JSON parsing error: {str(e)}",
                "raw_response": response.text if 'response' in locals() else None
            }
        except Exception as e:
            print(f"Error in comprehensive analysis: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def save_comprehensive_analysis_to_db(
        self,
        db: Session,
        analysis_result: Dict,
        video_clip_path: Optional[str] = None
    ) -> Optional[SceneAnalysis]:
        """
        Save comprehensive structured analysis to database

        Args:
            db: Database session
            analysis_result: Result from analyze_comprehensive_structured()
            video_clip_path: Path to video clip

        Returns:
            SceneAnalysis record or None if error
        """
        if not analysis_result.get('success'):
            print(f"Cannot save failed analysis: {analysis_result.get('error')}")
            return None

        try:
            structured_data = analysis_result['structured_analysis']
            scene_data = structured_data.get('scene', {})
            metadata = structured_data.get('metadata', {})
            time_window = structured_data.get('time_window', {})

            # Create SceneAnalysis record
            scene_analysis = SceneAnalysis(
                timestamp=datetime.utcnow(),
                time_window_start=time_window.get('start', '00:00'),
                time_window_end=time_window.get('end', '00:10'),
                video_clip_path=video_clip_path,
                overall_summary=scene_data.get('overall_summary', ''),
                crowd_density=scene_data.get('crowd_density', 'unknown'),
                energy_level=scene_data.get('energy_level', 'unknown'),
                dominant_activities=scene_data.get('dominant_activities', []),
                environmental_context=scene_data.get('environmental_context'),
                anomalies_detected=scene_data.get('anomalies_detected', []),
                gemini_model=metadata.get('gemini_model', 'gemini-2.5-flash'),
                confidence_score=metadata.get('confidence_score'),
                full_structured_response=structured_data
            )

            db.add(scene_analysis)
            db.commit()
            db.refresh(scene_analysis)

            # Save events
            for event_data in structured_data.get('events', []):
                event = EventLog(
                    scene_analysis_id=scene_analysis.id,
                    video_timestamp=event_data.get('timestamp', '00:00'),
                    event_type=event_data.get('event_type', 'unknown'),
                    severity=event_data.get('severity', 'normal'),
                    description=event_data.get('description', ''),
                    location=event_data.get('location', ''),
                    involved_tracking_ids=event_data.get('involved_tracking_ids', []),
                    requires_action=event_data.get('requires_action', False),
                    recommended_action=event_data.get('recommended_action')
                )
                db.add(event)

            # Save interactions
            for interaction_data in structured_data.get('interactions', []):
                interaction = InteractionLog(
                    scene_analysis_id=scene_analysis.id,
                    interaction_type=interaction_data.get('type', 'unknown'),
                    participants=interaction_data.get('participants', []),
                    location=interaction_data.get('location', ''),
                    description=interaction_data.get('description', ''),
                    duration_seconds=self._parse_duration(interaction_data.get('duration')),
                    outcome=interaction_data.get('outcome')
                )
                db.add(interaction)

            # Save individual behavior analyses
            for individual_data in structured_data.get('individuals', []):
                tracking_id = individual_data.get('body_tracking_id')
                person_id = individual_data.get('person_id')

                behavior = BehaviorAnalysis(
                    person_id=person_id,
                    body_tracking_id=tracking_id,
                    scene_analysis_id=scene_analysis.id,
                    detection_event_id=None,  # Will be linked separately if needed
                    analysis_type='comprehensive_individual',
                    analysis_text=json.dumps(individual_data, indent=2),
                    video_clip_path=video_clip_path,
                    structured_data=individual_data
                )
                db.add(behavior)

                # Save product-specific interactions from Gemini analysis
                for product_interaction in individual_data.get('product_interactions', []):
                    try:
                        # Get product from database if it exists
                        from app.core.database import Product
                        product_name = product_interaction.get('product_name')
                        product = db.query(Product).filter(Product.name == product_name).first() if product_name else None

                        # Create InteractionLog record with product context
                        product_inter_log = InteractionLog(
                            scene_analysis_id=scene_analysis.id,
                            interaction_type='customer_product',
                            participants=[tracking_id],
                            location=individual_data.get('location', {}).get('current_zone', 'Unknown'),
                            description=f"Product interaction: {', '.join(product_interaction.get('interaction_types', []))} with {product_name}",
                            duration_seconds=product_interaction.get('interaction_duration_seconds'),
                            outcome='ongoing',
                            product_names=[product_name] if product_name else [],
                            engagement_score=product_interaction.get('engagement_level', 0) / 10.0 if product_interaction.get('engagement_level') else None
                        )
                        db.add(product_inter_log)

                    except Exception as e:
                        print(f"Warning: Could not save product interaction: {e}")
                        continue

                # Save gaze behavior data
                gaze_behavior = individual_data.get('gaze_behavior', {})
                if gaze_behavior.get('primary_focus_zone'):
                    try:
                        # Create interaction log for significant gaze events
                        gaze_inter_log = InteractionLog(
                            scene_analysis_id=scene_analysis.id,
                            interaction_type='customer_product',  # Gaze is a form of product interaction
                            participants=[tracking_id],
                            location=gaze_behavior.get('primary_focus_zone', 'Unknown'),
                            description=f"Gaze fixation: {gaze_behavior.get('visual_search_pattern', 'unknown')} pattern, {gaze_behavior.get('distraction_level', 'unknown')} distraction",
                            duration_seconds=gaze_behavior.get('attention_span_seconds'),
                            outcome='ongoing'
                        )
                        db.add(gaze_inter_log)
                    except Exception as e:
                        print(f"Warning: Could not save gaze interaction: {e}")

            db.commit()

            print(f"✅ Saved comprehensive analysis to database (Scene ID: {scene_analysis.id})")
            print(f"   - Events: {len(structured_data.get('events', []))}")
            print(f"   - Interactions: {len(structured_data.get('interactions', []))}")
            print(f"   - Individuals: {len(structured_data.get('individuals', []))}")
            product_interactions_count = sum(len(ind.get('product_interactions', [])) for ind in structured_data.get('individuals', []))
            if product_interactions_count > 0:
                print(f"   - Product interactions: {product_interactions_count}")
            return scene_analysis

        except Exception as e:
            print(f"Error saving comprehensive analysis to DB: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return None

    def _parse_duration(self, duration_str: Optional[str]) -> Optional[float]:
        """Parse duration string like '45s' or '2m30s' into seconds"""
        if not duration_str:
            return None

        try:
            # Simple parsing for common formats
            duration_str = duration_str.lower().strip()

            # Just seconds: "45s"
            if duration_str.endswith('s') and 'm' not in duration_str:
                return float(duration_str[:-1])

            # Minutes and seconds: "2m30s"
            if 'm' in duration_str:
                parts = duration_str.split('m')
                minutes = float(parts[0])
                seconds = float(parts[1].rstrip('s')) if len(parts) > 1 and parts[1] else 0
                return minutes * 60 + seconds

            # Try to parse as number
            return float(duration_str)

        except:
            return None

    # ==================== PRODUCT DETECTION IN ZONES ====================

    def analyze_products_in_zone(
        self,
        frame_path: str,
        zone_name: str,
        zone_type: str = "product"
    ) -> Dict[str, any]:
        """
        Analyze a frame and identify products visible in a specific zone

        Args:
            frame_path: Path to frame image
            zone_name: Name of the zone being analyzed
            zone_type: Type of zone

        Returns:
            Dictionary with detected products
        """
        try:
            # Read frame as bytes
            with open(frame_path, 'rb') as f:
                frame_bytes = f.read()

            prompt = f"""
            Analyze this retail store image focusing on the {zone_name} area.

            Identify ALL visible products in this zone and provide your response in STRICT JSON format:

            {{
              "products": [
                {{
                  "name": "Product Name",
                  "category": "Category (Electronics, Clothing, Food, etc.)",
                  "description": "Brief description",
                  "position": {{
                    "x": 0.0-1.0,
                    "y": 0.0-1.0,
                    "bounding_box": {{"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 0.0}},
                    "shelf_level": "top|middle|bottom"
                  }},
                  "confidence": 0.0-1.0,
                  "visibility": "fully_visible|partially_visible|obscured"
                }}
              ]
            }}

            COORDINATE SYSTEM:
            - All coordinates normalized between 0.0 and 1.0
            - (0.0, 0.0) = top-left corner
            - (1.0, 1.0) = bottom-right corner
            - Position x,y = center point of product
            - Bounding box = rectangular area containing product

            RULES:
            - Identify 3-10 distinct products (more if clearly visible)
            - Be specific with product names (e.g., "Wireless Mouse" not "Mouse")
            - Categorize accurately
            - Estimate position based on where product appears in image
            - Rate confidence honestly (0.0 to 1.0)

            Provide ONLY the JSON response with no additional text.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {"role": "user", "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": frame_bytes
                            }
                        },
                        {"text": prompt}
                    ]}
                ]
            )

            # Parse JSON response
            response_text = response.text.strip()

            # Try to extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            elif response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text.strip('`').strip()
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()

            product_data = json.loads(response_text)

            return {
                "products": product_data.get("products", []),
                "zone_name": zone_name,
                "zone_type": zone_type,
                "raw_response": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini JSON response: {e}")
            print(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            return {
                "error": f"JSON parsing error: {str(e)}",
                "raw_response": response.text if 'response' in locals() else None
            }
        except Exception as e:
            print(f"Error analyzing products in zone: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    # ==================== LAYOUT ZONE GENERATION ====================

    def analyze_layout_and_generate_zones(self, video_path: str, youtube_url: str = None) -> Dict[str, any]:
        """
        Analyze video layout and automatically generate zone configurations
        Returns zones and virtual lines in JSON format ready for database
        
        Args:
            video_path: Path to local video file
            youtube_url: Optional YouTube URL (preferred for faster processing)
        """
        try:
            import time
            
            # Prepare video input - prefer YouTube URL if available
            if youtube_url:
                print(f"Using YouTube URL directly: {youtube_url}")
                video_part = types.Part(
                    file_data=types.FileData(file_uri=youtube_url)
                )
            else:
                # Upload video file
                video_file = self.client.files.upload(file=video_path)
                
                # Wait for file to become active (Gemini API requirement)
                print("Waiting for file to process...")
                max_retries = 10
                for retry in range(max_retries):
                    file_status = self.client.files.get(name=video_file.name)
                    if file_status.state.name == "ACTIVE":
                        print("File is ready for analysis")
                        break
                    if retry < max_retries - 1:
                        time.sleep(2)
                        print(f"  Waiting... ({retry + 1}/{max_retries})")
                
                video_part = video_file
            
            prompt = """
            Analyze this retail store surveillance video and identify the store layout to create optimal tracking zones.

            IMPORTANT: Provide your response in STRICT JSON format with the following structure:

            {
              "zones": [
                {
                  "name": "Zone Name",
                  "zone_type": "entrance|checkout|product|aisle|queue",
                  "polygon_points": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                  "color": "#HEXCOLOR",
                  "max_capacity": number,
                  "description": "Brief description"
                }
              ],
              "virtual_lines": [
                {
                  "name": "Line Name",
                  "start_point": {"x": x_value, "y": y_value},
                  "end_point": {"x": x_value, "y": y_value},
                  "count_direction": "both|in|out",
                  "color": "#HEXCOLOR",
                  "description": "Brief description"
                }
              ]
            }

            COORDINATE SYSTEM:
            - All coordinates must be normalized between 0.0 and 1.0
            - (0.0, 0.0) = top-left corner of frame
            - (1.0, 1.0) = bottom-right corner of frame
            - (0.5, 0.5) = center of frame

            ZONES TO IDENTIFY:
            1. Entrance/Exit zones (where people enter/leave the store)
            2. Checkout/Queue zones (payment counters, waiting areas)
            3. Product zones (specific product displays, shelves, departments)
            4. Aisle zones (main traffic pathways between sections)
            5. High-traffic areas

            VIRTUAL LINES TO PLACE:
            1. Entrance counting line (across entry points)
            2. Exit counting line (across exit points)
            3. Checkout lines (at payment counters)
            4. Zone transition lines (between major sections)

            RULES:
            - Create 4-8 zones total (don't over-segment)
            - Zones should not overlap significantly
            - Use appropriate zone_types: "entrance", "checkout", "product", "aisle", "queue"
            - Use distinct colors for different zone types
            - Polygon points should form valid rectangles or polygons (4+ corners)
            - Virtual lines should be placed at natural transition points
            - count_direction: "both" for entrance/exit, "in" for checkout entry, "out" for exits

            Analyze the video carefully and provide ONLY the JSON response with no additional text.
            """

            response = self.client.models.generate_content(
                model=self.model,
                contents=[video_part, prompt]
            )

            # Parse the JSON response
            response_text = response.text.strip()
            
            # Try to extract JSON from response (remove markdown code blocks if present)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            elif response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text.strip('`').strip()
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()
            
            zone_config = json.loads(response_text)
            
            return {
                "zones": zone_config.get("zones", []),
                "virtual_lines": zone_config.get("virtual_lines", []),
                "raw_response": response.text,
                "timestamp": datetime.utcnow().isoformat()
            }

        except json.JSONDecodeError as e:
            print(f"Error parsing Gemini JSON response: {e}")
            print(f"Raw response: {response.text}")
            return {
                "error": f"JSON parsing error: {str(e)}",
                "raw_response": response.text
            }
        except Exception as e:
            print(f"Error in layout analysis: {e}")
            return {"error": str(e)}
