"""
Customer Recognition Agent
Re-identify returning customers using appearance embeddings (CLIP)
"""

import torch
import numpy as np
from PIL import Image
import cv2
from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
import pickle
import uuid

try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    print("[Customer Recognition] WARNING: transformers not installed. Customer recognition disabled.")
    print("  Install with: pip install transformers torch")

from app.core.database import CustomerProfile, CustomerVisit, AppearanceMatch


class CustomerRecognitionAgent:
    """Recognize returning customers across visits using CLIP embeddings"""

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        similarity_threshold: float = 0.85,
        temporal_window_days: int = 90,
        enabled: bool = True
    ):
        """
        Initialize customer recognition

        Args:
            model_name: CLIP model to use for embeddings
            similarity_threshold: Minimum cosine similarity for match (0.85 = 85%)
            temporal_window_days: Only match against profiles from last N days
            enabled: Enable/disable recognition (useful for testing)
        """
        self.enabled = enabled and CLIP_AVAILABLE
        self.similarity_threshold = similarity_threshold
        self.temporal_window_days = temporal_window_days

        if not self.enabled:
            print("[Customer Recognition] Disabled")
            return

        try:
            # Load CLIP model
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[Customer Recognition] Loading CLIP model on {self.device}...")

            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)

            print(f"[Customer Recognition] Initialized with {model_name}")

        except Exception as e:
            print(f"[Customer Recognition] ERROR loading CLIP: {e}")
            self.enabled = False

    def extract_appearance_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract appearance embedding from person crop

        Args:
            image: OpenCV image (BGR) of person crop

        Returns:
            Embedding vector (512-dim for CLIP base) or None if disabled
        """
        if not self.enabled:
            return None

        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)

            # Process with CLIP
            inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # Normalize embedding
                embedding = image_features / image_features.norm(p=2, dim=-1, keepdim=True)

            return embedding.cpu().numpy().flatten()

        except Exception as e:
            print(f"[Customer Recognition] Error extracting embedding: {e}")
            return None

    def find_matching_profile(
        self,
        db: Session,
        tracking_id: str,
        person_crop: np.ndarray
    ) -> Optional[Tuple[int, float]]:
        """
        Find matching customer profile for new detection

        Args:
            db: Database session
            tracking_id: Current body tracking ID
            person_crop: Image crop of detected person

        Returns:
            (profile_id, confidence_score) or None if no match
        """
        if not self.enabled:
            return None

        # Extract embedding
        embedding = self.extract_appearance_embedding(person_crop)
        if embedding is None:
            return None

        # Get recent profiles (within temporal window)
        cutoff_date = datetime.now(UTC) - timedelta(days=self.temporal_window_days)

        profiles = db.query(CustomerProfile).filter(
            CustomerProfile.last_visit >= cutoff_date,
            CustomerProfile.opt_out_date == None,
            CustomerProfile.appearance_embedding != None
        ).all()

        if not profiles:
            return None

        # Find best match
        best_match = None
        best_score = 0

        for profile in profiles:
            try:
                # Deserialize embedding
                stored_embedding = pickle.loads(profile.appearance_embedding)

                # Calculate cosine similarity
                similarity = self._cosine_similarity(embedding, stored_embedding)

                # Temporal plausibility (penalize very recent visits)
                time_since_last_visit = (datetime.now(UTC) - profile.last_visit).total_seconds() / 3600
                temporal_score = min(1.0, time_since_last_visit / 24)  # Full score after 24h

                # Combined score
                combined_score = similarity * 0.8 + temporal_score * 0.2

                if combined_score > best_score and similarity >= self.similarity_threshold:
                    best_score = combined_score
                    best_match = profile.id

            except Exception as e:
                print(f"[Customer Recognition] Error matching profile {profile.id}: {e}")
                continue

        # Log match attempt
        match_log = AppearanceMatch(
            tracking_id=tracking_id,
            matched_profile_id=best_match,
            confidence_score=best_score if best_match else 0,
            embedding_distance=1 - best_score if best_match else 1.0,
            visual_similarity=best_score if best_match else 0,
            match_accepted=best_match is not None
        )
        db.add(match_log)
        db.commit()

        if best_match:
            print(f"[Customer Recognition] Matched tracking {tracking_id} to profile {best_match} (confidence: {best_score:.2f})")
            return (best_match, best_score)

        return None

    def create_new_profile(
        self,
        db: Session,
        tracking_id: str,
        person_crop: np.ndarray
    ) -> Optional[int]:
        """
        Create new customer profile for first-time visitor

        Args:
            db: Database session
            tracking_id: Body tracking ID
            person_crop: Image crop of person

        Returns:
            profile_id of newly created profile, or None if disabled
        """
        if not self.enabled:
            return None

        embedding = self.extract_appearance_embedding(person_crop)
        if embedding is None:
            return None

        try:
            profile = CustomerProfile(
                profile_uuid=str(uuid.uuid4()),
                appearance_embedding=pickle.dumps(embedding),
                first_visit=datetime.now(UTC),
                last_visit=datetime.now(UTC),
                total_visits=1,
                favorite_zones=[],
                avg_visit_duration_minutes=0,
                avg_purchase_intent_score=0.5
            )

            db.add(profile)
            db.commit()
            db.refresh(profile)

            print(f"[Customer Recognition] Created new profile {profile.id} for tracking {tracking_id}")
            return profile.id

        except Exception as e:
            print(f"[Customer Recognition] Error creating profile: {e}")
            db.rollback()
            return None

    def update_profile_from_visit(
        self,
        db: Session,
        profile_id: int,
        tracking_id: str,
        session_data: Dict,
        new_crop: Optional[np.ndarray] = None
    ):
        """
        Update customer profile after visit

        Args:
            profile_id: Customer profile ID
            tracking_id: Body tracking ID for this visit
            session_data: Visit session data (zones, duration, etc.)
            new_crop: Updated person crop for embedding refresh
        """
        if not self.enabled:
            return

        try:
            profile = db.query(CustomerProfile).filter(
                CustomerProfile.id == profile_id
            ).first()

            if not profile:
                return

            # Update visit counts
            profile.last_visit = datetime.now(UTC)
            profile.total_visits += 1

            # Update favorite zones
            visited_zones = session_data.get('zones_visited', [])
            current_favorites = profile.favorite_zones or []

            # Increment zone visit counts
            zone_counts = {z: current_favorites.count(z) for z in set(current_favorites + visited_zones)}
            for zone in visited_zones:
                zone_counts[zone] = zone_counts.get(zone, 0) + 1

            # Keep top 5 zones
            profile.favorite_zones = sorted(zone_counts.keys(),
                                           key=lambda z: zone_counts[z],
                                           reverse=True)[:5]

            # Update average visit duration
            duration = session_data.get('duration_minutes', 0)
            if profile.avg_visit_duration_minutes:
                profile.avg_visit_duration_minutes = (
                    profile.avg_visit_duration_minutes * 0.8 + duration * 0.2
                )
            else:
                profile.avg_visit_duration_minutes = duration

            # Refresh embedding if provided
            if new_crop is not None:
                new_embedding = self.extract_appearance_embedding(new_crop)
                if new_embedding is not None and profile.appearance_embedding:
                    # Blend with old embedding (80% new, 20% old for stability)
                    old_embedding = pickle.loads(profile.appearance_embedding)
                    blended = new_embedding * 0.8 + old_embedding * 0.2
                    profile.appearance_embedding = pickle.dumps(blended)
                    profile.embedding_updated_at = datetime.now(UTC)

            # Create visit record
            visit = CustomerVisit(
                profile_id=profile_id,
                visit_date=datetime.now(UTC),
                tracking_ids=[tracking_id],
                zones_visited=visited_zones,
                duration_minutes=duration,
                purchase_intent_score=session_data.get('purchase_intent', 0.5)
            )

            db.add(visit)
            db.commit()

            print(f"[Customer Recognition] Updated profile {profile_id} (Visit #{profile.total_visits})")

        except Exception as e:
            print(f"[Customer Recognition] Error updating profile: {e}")
            db.rollback()

    def get_customer_insights(
        self,
        db: Session,
        profile_id: int
    ) -> Dict:
        """
        Generate insights for customer profile

        Args:
            db: Database session
            profile_id: Customer profile ID

        Returns:
            Dictionary with customer insights for staff
        """
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.id == profile_id
        ).first()

        if not profile:
            return {}

        # Get recent visits
        recent_visits = db.query(CustomerVisit).filter(
            CustomerVisit.profile_id == profile_id
        ).order_by(CustomerVisit.visit_date.desc()).limit(5).all()

        insights = {
            "profile_id": profile.id,
            "profile_uuid": profile.profile_uuid,
            "is_vip": profile.vip_status,
            "total_visits": profile.total_visits,
            "visit_frequency": self._calculate_visit_frequency(profile, recent_visits),
            "favorite_zones": profile.favorite_zones,
            "avg_visit_duration": round(profile.avg_visit_duration_minutes or 0, 1),
            "purchase_likelihood": self._estimate_purchase_likelihood(profile, recent_visits),
            "recommended_approach": self._generate_approach_recommendation(profile, recent_visits),
            "last_visit_days_ago": (datetime.now(UTC) - profile.last_visit).days
        }

        return insights

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _calculate_visit_frequency(
        self,
        profile: CustomerProfile,
        recent_visits: List[CustomerVisit]
    ) -> str:
        """Estimate visit frequency"""
        if profile.total_visits < 2:
            return "first_time"

        if len(recent_visits) < 2:
            return "infrequent"

        # Calculate average days between visits
        visit_dates = [v.visit_date for v in recent_visits]
        visit_dates.sort()

        gaps = [(visit_dates[i+1] - visit_dates[i]).days
                for i in range(len(visit_dates)-1)]

        avg_gap = sum(gaps) / len(gaps)

        if avg_gap <= 3:
            return "daily"
        elif avg_gap <= 10:
            return "weekly"
        elif avg_gap <= 40:
            return "monthly"
        else:
            return "occasional"

    def _estimate_purchase_likelihood(
        self,
        profile: CustomerProfile,
        recent_visits: List[CustomerVisit]
    ) -> float:
        """Estimate likelihood of purchase (0-1)"""
        if not recent_visits:
            return 0.5

        # Factor 1: Historical purchase intent
        avg_intent = profile.avg_purchase_intent_score or 0.5

        # Factor 2: Visit frequency (frequent = higher)
        frequency_boost = min(0.2, profile.total_visits * 0.02)

        # Factor 3: Recent visit duration (longer = higher)
        duration_boost = min(0.2, profile.avg_visit_duration_minutes / 60 * 0.1)

        return min(1.0, avg_intent + frequency_boost + duration_boost)

    def _generate_approach_recommendation(
        self,
        profile: CustomerProfile,
        recent_visits: List[CustomerVisit]
    ) -> str:
        """Generate recommendation for staff on how to approach"""
        if profile.vip_status:
            return "VIP customer - prioritize personalized service"

        if profile.total_visits == 1:
            return "First-time visitor - offer general assistance and store orientation"

        frequency = self._calculate_visit_frequency(profile, recent_visits)

        if frequency in ["daily", "weekly"]:
            return "Regular customer - acknowledge familiarity, ask if looking for something specific"

        if profile.avg_purchase_intent_score and profile.avg_purchase_intent_score > 0.7:
            return "High purchase intent - offer product recommendations and assistance"

        return "Returning customer - friendly greeting, offer help if needed"
