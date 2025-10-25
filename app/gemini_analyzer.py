from google import genai
from google.genai import types
import os
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

    def analyze_behavior(self, video_path: str) -> Dict[str, str]:
        """
        Analyze person behavior from video clip
        Returns detailed analysis of behavior, clothing, emotions, pathway, and interests
        """
        try:
            # Upload video file
            video_file = self.client.files.upload(file=video_path)

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
                contents=[video_file, prompt]
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

    def analyze_with_custom_fps(self, video_path: str, fps: int = 2) -> Dict[str, str]:
        """
        Analyze video with custom frame sampling rate
        Higher FPS for detailed action analysis
        """
        try:
            with open(video_path, 'rb') as f:
                video_bytes = f.read()

            prompt = """
            Analyze this video clip with focus on detailed movements and actions:
            - Track the person's exact pathway
            - Note every interaction or point of interest
            - Identify products or areas examined
            - Provide timestamps for key actions

            Be very detailed in your analysis.
            """

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
            video_file = self.client.files.upload(file=video_path)

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
