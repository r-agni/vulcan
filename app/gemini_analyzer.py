from google import genai
from google.genai import types
import os
import json
import re
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database import BehaviorAnalysis
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
