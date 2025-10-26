"""
Product Interaction Tracker
Tracks specific product interactions by combining gaze detection, hand tracking, and product positions
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from dataclasses import dataclass
from app.core.database import ProductInteractionEvent, ProductEngagementMetrics, Product
from app.inventory.product_detector import ProductDetector
from app.detection.gaze_detector import GazeDetector
from app.detection.interaction_detector import InteractionDetector


@dataclass
class ProductInteraction:
    """Data class for active product interaction"""
    tracking_id: str
    person_id: Optional[int]
    product_id: int
    product_name: str
    zone_id: int
    interaction_type: str  # gazing, reaching, touching, picking_up, examining, putting_back
    start_time: datetime
    duration_seconds: float = 0.0
    engagement_score: float = 0.0
    hand_position: Optional[Tuple[float, float]] = None
    gesture_type: Optional[str] = None
    gaze_duration: float = 0.0
    confidence: float = 0.0


class ProductInteractionTracker:
    """
    Track product-specific interactions by combining multiple detection systems
    """

    def __init__(
        self,
        product_detector: ProductDetector,
        gaze_detector: GazeDetector,
        interaction_detector: InteractionDetector
    ):
        """
        Initialize product interaction tracker

        Args:
            product_detector: ProductDetector instance
            gaze_detector: GazeDetector instance
            interaction_detector: InteractionDetector instance
        """
        self.product_detector = product_detector
        self.gaze_detector = gaze_detector
        self.interaction_detector = interaction_detector

        # Active interactions: (tracking_id, product_id) -> ProductInteraction
        self.active_interactions: Dict[Tuple[str, int], ProductInteraction] = {}

        # Gaze tracking: tracking_id -> {product_id: gaze_start_time}
        self.gaze_tracking: Dict[str, Dict[int, datetime]] = {}

    def update(
        self,
        tracking_id: str,
        person_id: Optional[int],
        zone_id: int,
        hand_position: Optional[Tuple[float, float]],
        gesture_type: Optional[str],
        gaze_target_position: Optional[Tuple[float, float]],
        timestamp: datetime,
        db: Session
    ) -> List[ProductInteraction]:
        """
        Update product interactions for a person

        Args:
            tracking_id: Person tracking ID
            person_id: Person ID (if known)
            zone_id: Current zone ID
            hand_position: Hand position if detected
            gesture_type: Hand gesture type if detected
            gaze_target_position: Gaze target position if detected
            timestamp: Current timestamp
            db: Database session

        Returns:
            List of active product interactions
        """
        interactions = []

        # Get products in this zone
        products = self.product_detector.get_products_in_zone(zone_id, db)

        if not products:
            return interactions

        # Track gaze-based product interactions
        if gaze_target_position:
            gaze_product = self.product_detector.find_nearest_product(
                gaze_target_position,
                zone_id,
                db,
                max_distance=0.15
            )

            if gaze_product:
                product_id = gaze_product['id']
                interaction = self._update_gaze_interaction(
                    tracking_id,
                    person_id,
                    gaze_product,
                    zone_id,
                    timestamp
                )
                if interaction:
                    interactions.append(interaction)

        # Track hand-based product interactions
        if hand_position and gesture_type:
            hand_product = self.product_detector.find_nearest_product(
                hand_position,
                zone_id,
                db,
                max_distance=0.12  # Tighter threshold for hand interactions
            )

            if hand_product:
                product_id = hand_product['id']
                interaction = self._update_hand_interaction(
                    tracking_id,
                    person_id,
                    hand_product,
                    zone_id,
                    hand_position,
                    gesture_type,
                    timestamp
                )
                if interaction:
                    interactions.append(interaction)

        # Update durations for all active interactions
        self._update_interaction_durations(timestamp)

        return interactions

    def _update_gaze_interaction(
        self,
        tracking_id: str,
        person_id: Optional[int],
        product: Dict,
        zone_id: int,
        timestamp: datetime
    ) -> Optional[ProductInteraction]:
        """
        Update or create gaze-based product interaction

        Args:
            tracking_id: Person tracking ID
            person_id: Person ID
            product: Product dictionary
            zone_id: Zone ID
            timestamp: Current timestamp

        Returns:
            ProductInteraction or None
        """
        product_id = product['id']
        product_name = product['name']

        # Track gaze start time
        if tracking_id not in self.gaze_tracking:
            self.gaze_tracking[tracking_id] = {}

        if product_id not in self.gaze_tracking[tracking_id]:
            # New gaze on this product
            self.gaze_tracking[tracking_id][product_id] = timestamp

        gaze_start = self.gaze_tracking[tracking_id][product_id]
        gaze_duration = (timestamp - gaze_start).total_seconds()

        # Create or update interaction
        key = (tracking_id, product_id)

        if key in self.active_interactions:
            # Update existing interaction
            interaction = self.active_interactions[key]
            interaction.gaze_duration = gaze_duration
            interaction.duration_seconds = (timestamp - interaction.start_time).total_seconds()

            # Update engagement score
            interaction.engagement_score = min(1.0, gaze_duration / 10.0)  # Max at 10 seconds
        else:
            # Create new interaction
            interaction = ProductInteraction(
                tracking_id=tracking_id,
                person_id=person_id,
                product_id=product_id,
                product_name=product_name,
                zone_id=zone_id,
                interaction_type="gazing",
                start_time=timestamp,
                gaze_duration=gaze_duration,
                engagement_score=min(1.0, gaze_duration / 10.0),
                confidence=0.7
            )
            self.active_interactions[key] = interaction

        return interaction

    def _update_hand_interaction(
        self,
        tracking_id: str,
        person_id: Optional[int],
        product: Dict,
        zone_id: int,
        hand_position: Tuple[float, float],
        gesture_type: str,
        timestamp: datetime
    ) -> Optional[ProductInteraction]:
        """
        Update or create hand-based product interaction

        Args:
            tracking_id: Person tracking ID
            person_id: Person ID
            product: Product dictionary
            zone_id: Zone ID
            hand_position: Hand position
            gesture_type: Gesture type
            timestamp: Current timestamp

        Returns:
            ProductInteraction or None
        """
        product_id = product['id']
        product_name = product['name']
        key = (tracking_id, product_id)

        # Determine interaction type based on gesture
        interaction_type = self._classify_interaction_type(gesture_type)

        if key in self.active_interactions:
            # Update existing interaction
            interaction = self.active_interactions[key]
            previous_type = interaction.interaction_type

            # Update interaction type (progression)
            interaction.interaction_type = self._progress_interaction_type(
                previous_type,
                interaction_type,
                gesture_type
            )

            interaction.hand_position = hand_position
            interaction.gesture_type = gesture_type
            interaction.duration_seconds = (timestamp - interaction.start_time).total_seconds()

            # Update engagement score
            interaction.engagement_score = self._calculate_engagement_score(
                interaction.interaction_type,
                interaction.duration_seconds,
                interaction.gaze_duration
            )
        else:
            # Create new interaction
            interaction = ProductInteraction(
                tracking_id=tracking_id,
                person_id=person_id,
                product_id=product_id,
                product_name=product_name,
                zone_id=zone_id,
                interaction_type=interaction_type,
                start_time=timestamp,
                hand_position=hand_position,
                gesture_type=gesture_type,
                engagement_score=0.5,
                confidence=0.8
            )
            self.active_interactions[key] = interaction

        return interaction

    def _classify_interaction_type(self, gesture_type: str) -> str:
        """
        Classify interaction type based on gesture

        Args:
            gesture_type: Hand gesture type

        Returns:
            Interaction type string
        """
        if gesture_type == "pointing":
            return "reaching"
        elif gesture_type == "open_palm":
            return "touching"
        elif gesture_type == "grabbing":
            return "picking_up"
        elif gesture_type == "holding":
            return "examining"
        else:
            return "touching"

    def _progress_interaction_type(
        self,
        current_type: str,
        new_type: str,
        gesture: str
    ) -> str:
        """
        Progress interaction type based on gesture transitions

        Args:
            current_type: Current interaction type
            new_type: New interaction type from gesture
            gesture: Current gesture

        Returns:
            Progressed interaction type
        """
        # Transition rules
        if current_type == "gazing" and new_type in ["reaching", "touching"]:
            return new_type

        if current_type == "reaching" and gesture == "grabbing":
            return "picking_up"

        if current_type == "picking_up" and gesture == "holding":
            return "examining"

        if current_type == "examining" and gesture == "open_palm":
            return "putting_back"

        # Default: keep new type
        return new_type

    def _calculate_engagement_score(
        self,
        interaction_type: str,
        duration: float,
        gaze_duration: float
    ) -> float:
        """
        Calculate engagement score based on interaction characteristics

        Args:
            interaction_type: Type of interaction
            duration: Interaction duration in seconds
            gaze_duration: Gaze duration in seconds

        Returns:
            Engagement score (0.0-1.0)
        """
        base_scores = {
            "gazing": 0.3,
            "reaching": 0.4,
            "touching": 0.5,
            "picking_up": 0.7,
            "examining": 0.9,
            "putting_back": 0.6
        }

        base_score = base_scores.get(interaction_type, 0.3)

        # Boost based on duration
        duration_boost = min(0.3, duration / 20.0)  # Max 0.3 boost over 20 seconds

        # Boost based on gaze
        gaze_boost = min(0.2, gaze_duration / 15.0)  # Max 0.2 boost over 15 seconds

        return min(1.0, base_score + duration_boost + gaze_boost)

    def _update_interaction_durations(self, timestamp: datetime):
        """
        Update durations for all active interactions

        Args:
            timestamp: Current timestamp
        """
        for interaction in self.active_interactions.values():
            interaction.duration_seconds = (timestamp - interaction.start_time).total_seconds()

    def end_interaction(
        self,
        tracking_id: str,
        product_id: int,
        db: Session
    ) -> Optional[ProductInteraction]:
        """
        End an active product interaction and save to database

        Args:
            tracking_id: Person tracking ID
            product_id: Product ID
            db: Database session

        Returns:
            Ended ProductInteraction or None
        """
        key = (tracking_id, product_id)

        if key in self.active_interactions:
            interaction = self.active_interactions.pop(key)

            # Save to database
            self._save_interaction_to_db(interaction, db)

            # Update product metrics
            self._update_product_metrics(product_id, interaction, db)

            # Clear gaze tracking
            if tracking_id in self.gaze_tracking:
                if product_id in self.gaze_tracking[tracking_id]:
                    del self.gaze_tracking[tracking_id][product_id]

            return interaction

        return None

    def _save_interaction_to_db(
        self,
        interaction: ProductInteraction,
        db: Session
    ):
        """
        Save product interaction to database

        Args:
            interaction: ProductInteraction object
            db: Database session
        """
        try:
            # Determine outcome
            outcome = None
            if interaction.interaction_type == "picking_up":
                outcome = "picked_up"
            elif interaction.interaction_type == "putting_back":
                outcome = "put_back"
            elif interaction.interaction_type == "examining":
                outcome = "examined"
            elif interaction.duration_seconds < 1.0:
                outcome = "ignored"

            # Create database record
            db_interaction = ProductInteractionEvent(
                person_id=interaction.person_id,
                body_tracking_id=interaction.tracking_id,
                product_id=interaction.product_id,
                zone_id=interaction.zone_id,
                timestamp=interaction.start_time,
                interaction_type=interaction.interaction_type,
                duration_seconds=interaction.duration_seconds,
                engagement_score=interaction.engagement_score,
                hand_position={'x': interaction.hand_position[0], 'y': interaction.hand_position[1]} if interaction.hand_position else None,
                gesture_type=interaction.gesture_type,
                gaze_duration_seconds=interaction.gaze_duration,
                gaze_confidence=interaction.confidence,
                interaction_ended=True,
                outcome=outcome,
                confidence_score=interaction.confidence
            )

            db.add(db_interaction)
            db.commit()

        except Exception as e:
            db.rollback()
            print(f"Error saving product interaction to DB: {e}")
            import traceback
            traceback.print_exc()

    def _update_product_metrics(
        self,
        product_id: int,
        interaction: ProductInteraction,
        db: Session
    ):
        """
        Update product engagement metrics

        Args:
            product_id: Product ID
            interaction: ProductInteraction object
            db: Database session
        """
        try:
            metrics = db.query(ProductEngagementMetrics).filter(
                ProductEngagementMetrics.product_id == product_id
            ).first()

            if not metrics:
                # Create new metrics record
                metrics = ProductEngagementMetrics(
                    product_id=product_id,
                    total_views=0,
                    total_touches=0,
                    total_pickups=0
                )
                db.add(metrics)

            # Update counters
            if interaction.gaze_duration > 0:
                metrics.total_views += 1
                metrics.total_view_duration_seconds += interaction.gaze_duration

            if interaction.interaction_type in ["touching", "reaching"]:
                metrics.total_touches += 1

            if interaction.interaction_type in ["picking_up", "examining"]:
                metrics.total_pickups += 1

            if interaction.interaction_type == "putting_back":
                metrics.total_putbacks += 1

            # Update engagement time
            metrics.total_engagement_time_seconds += interaction.duration_seconds

            # Recalculate averages
            if metrics.total_views > 0:
                metrics.avg_view_duration = metrics.total_view_duration_seconds / metrics.total_views

            total_interactions = metrics.total_touches + metrics.total_pickups
            if total_interactions > 0:
                metrics.avg_engagement_score = (
                    (metrics.avg_engagement_score * (total_interactions - 1) + interaction.engagement_score) /
                    total_interactions
                )

            # Update purchase intent based on interaction type
            if interaction.interaction_type == "examining":
                metrics.purchase_intent_score = min(1.0, metrics.purchase_intent_score + 0.1)
            elif interaction.interaction_type == "picking_up":
                metrics.purchase_intent_score = min(1.0, metrics.purchase_intent_score + 0.15)
                metrics.estimated_conversions += 1

            metrics.last_interaction = datetime.now(UTC)
            metrics.updated_at = datetime.now(UTC)

            db.commit()

        except Exception as e:
            db.rollback()
            print(f"Error updating product metrics: {e}")
            import traceback
            traceback.print_exc()

    def get_active_interactions(self) -> List[ProductInteraction]:
        """Get all active product interactions"""
        return list(self.active_interactions.values())

    def cleanup_old_interactions(
        self,
        db: Session,
        max_age_seconds: float = 10.0
    ):
        """
        Clean up old inactive interactions

        Args:
            db: Database session
            max_age_seconds: Maximum age before cleanup
        """
        current_time = datetime.now(UTC)
        keys_to_remove = []

        for key, interaction in self.active_interactions.items():
            age = (current_time - interaction.start_time).total_seconds()
            if age > max_age_seconds:
                keys_to_remove.append(key)

        # End and save old interactions
        for key in keys_to_remove:
            tracking_id, product_id = key
            self.end_interaction(tracking_id, product_id, db)

        # Clean up old gaze tracking
        for tracking_id in list(self.gaze_tracking.keys()):
            for product_id in list(self.gaze_tracking[tracking_id].keys()):
                gaze_start = self.gaze_tracking[tracking_id][product_id]
                if (current_time - gaze_start).total_seconds() > max_age_seconds:
                    del self.gaze_tracking[tracking_id][product_id]

            if not self.gaze_tracking[tracking_id]:
                del self.gaze_tracking[tracking_id]
