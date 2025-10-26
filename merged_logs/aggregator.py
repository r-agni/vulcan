"""
Data Aggregator for Merged Logs
Collects analytics data from all sources into a single snapshot
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json


def collect_analytics_snapshot(
    # Current metrics from main.py
    current_metrics: Dict[str, Any],

    # Zone and line configuration
    zones_data: list,
    lines_data: list,

    # Active tracking data
    active_persons: Dict,
    current_detections: list,

    # Analytics components
    trajectory_tracker: Any,
    dwell_calculator: Any,
    occupancy_counter: Any,
    line_crossing_detector: Any,
    queue_detector: Any,
    heatmap_generator: Any,
    interaction_tracker: Any,
    gaze_detector: Any,

    # AI Analysis
    gemini_analysis_text: Optional[str] = None,
    gemini_structured_data: Optional[Dict] = None,

    # Alert data
    alert_manager: Any = None,

    # Product inventory components (NEW)
    product_detector: Any = None,
    product_interaction_tracker: Any = None,
    db_session: Any = None,

    # Camera info
    camera_name: str = "Main Store Camera",
    camera_source: str = "",
    room_name: str = "Store Floor 1"
) -> Dict[str, Any]:
    """
    Aggregate all analytics data into a single snapshot dictionary
    This will be called every 5 seconds synchronized with Gemini analysis
    """

    snapshot = {
        'timestamp': datetime.utcnow(),

        # Camera Info
        'camera_name': camera_name,
        'camera_source': camera_source,
        'room_name': room_name,

        # Zones & Lines Config
        'zones': zones_data,
        'virtual_lines': lines_data,

        # Real-Time Occupancy Metrics (from current_metrics)
        'occupancy': current_metrics.get('occupancy', 0),
        'peak_today': current_metrics.get('peak_today', 0),
        'avg_dwell_time': current_metrics.get('avg_dwell_time', 0.0),
        'active_trajectories': current_metrics.get('active_trajectories', 0),
        'total_entries': current_metrics.get('total_entries', 0),
        'active_zones': current_metrics.get('active_zones', 0),
    }

    # Detection Data
    detected_person_ids = []
    detected_tracking_ids = []
    face_detection_count = 0
    unknown_person_count = 0

    for tracking_id, person_data in active_persons.items():
        detected_tracking_ids.append(tracking_id)
        person_id = person_data.get('person_id')
        if person_id:
            detected_person_ids.append(person_id)
            face_detection_count += 1
        else:
            unknown_person_count += 1

    snapshot.update({
        'detected_person_ids': detected_person_ids,
        'detected_tracking_ids': detected_tracking_ids,
        'detection_count': len(current_detections),
        'face_detection_count': face_detection_count,
        'unknown_person_count': unknown_person_count,
    })

    # Tracking Data (active sessions)
    active_sessions_data = []
    try:
        # Extract session data from active_persons
        for tracking_id, person_data in active_persons.items():
            session_info = {
                'tracking_id': tracking_id,
                'person_id': person_data.get('person_id'),
                'zone': person_data.get('zone', {}).get('name') if person_data.get('zone') else None,
                'last_seen': person_data.get('last_seen').isoformat() if person_data.get('last_seen') else None
            }
            active_sessions_data.append(session_info)
    except Exception as e:
        print(f"Error collecting session data: {e}")

    snapshot['active_sessions'] = active_sessions_data
    snapshot['session_count'] = len(active_sessions_data)

    # Per-Zone Analytics
    zone_occupancy_dict = {}
    zone_dwell_times_dict = {}

    try:
        for zone in zones_data:
            zone_id = zone.get('id')
            if zone_id:
                zone_occupancy_dict[zone_id] = occupancy_counter.get_occupancy(zone_id)

                # Calculate average dwell time for this zone
                zone_dwells = []
                for (person_id, z_id), entry_data in dwell_calculator.zone_entries.items():
                    if z_id == zone_id:
                        dwell_time = (datetime.utcnow() - entry_data['entry_time']).total_seconds()
                        zone_dwells.append(dwell_time)

                if zone_dwells:
                    zone_dwell_times_dict[zone_id] = sum(zone_dwells) / len(zone_dwells)
                else:
                    zone_dwell_times_dict[zone_id] = 0.0
    except Exception as e:
        print(f"Error collecting zone analytics: {e}")

    snapshot['zone_occupancy'] = zone_occupancy_dict
    snapshot['zone_dwell_times'] = zone_dwell_times_dict

    # Movement/Trajectory Data
    trajectories_data = []
    try:
        for tracking_id, path in trajectory_tracker.active_trajectories.items():
            trajectory_info = {
                'tracking_id': tracking_id,
                'path': [
                    {
                        'x': point['x'],
                        'y': point['y'],
                        'time': point['timestamp'].isoformat() if isinstance(point['timestamp'], datetime) else str(point['timestamp']),
                        'zone_id': point.get('zone_id')
                    }
                    for point in path[-50:]  # Last 50 points to keep data size manageable
                ]
            }
            trajectories_data.append(trajectory_info)
    except Exception as e:
        print(f"Error collecting trajectory data: {e}")

    snapshot['trajectories'] = trajectories_data
    snapshot['trajectory_count'] = len(trajectories_data)

    # Line Crossing Stats
    line_in_total = 0
    line_out_total = 0
    recent_crossings_data = []

    try:
        for line_id, counts in line_crossing_detector.crossing_counts.items():
            line_in_total += counts.get('in', 0)
            line_out_total += counts.get('out', 0)
    except Exception as e:
        print(f"Error collecting line crossing data: {e}")

    snapshot['line_crossings_in'] = line_in_total
    snapshot['line_crossings_out'] = line_out_total
    snapshot['recent_crossings'] = recent_crossings_data  # Could be enhanced to track recent crossings

    # Dwell Time Stats
    current_dwell_events_data = []
    max_dwell = None
    min_dwell = None

    try:
        for (person_id, zone_id), entry_data in dwell_calculator.zone_entries.items():
            dwell_time = (datetime.utcnow() - entry_data['entry_time']).total_seconds()
            current_dwell_events_data.append({
                'tracking_id': str(person_id),  # person_id used as tracking_id in current implementation
                'zone_id': zone_id,
                'duration': dwell_time
            })

            if max_dwell is None or dwell_time > max_dwell:
                max_dwell = dwell_time
            if min_dwell is None or dwell_time < min_dwell:
                min_dwell = dwell_time
    except Exception as e:
        print(f"Error collecting dwell time data: {e}")

    snapshot['current_dwell_events'] = current_dwell_events_data
    snapshot['max_dwell_time_current'] = max_dwell
    snapshot['min_dwell_time_current'] = min_dwell

    # Queue Analytics
    # Note: Queue detection would need to be called/available
    snapshot['active_queues'] = []  # Placeholder - would need queue detection results
    snapshot['queue_count'] = 0
    snapshot['max_queue_length'] = None

    # Heatmap Data
    try:
        snapshot['heatmap_path'] = None  # Would need to be passed in or retrieved
        snapshot['heatmap_intensity'] = float(heatmap_generator.heat_grid.max()) if hasattr(heatmap_generator, 'heat_grid') else None
    except Exception as e:
        snapshot['heatmap_path'] = None
        snapshot['heatmap_intensity'] = None

    # Product Interactions
    active_interactions_data = []
    try:
        active_interactions_list = interaction_tracker.get_active_interactions()
        for interaction in active_interactions_list:
            active_interactions_data.append({
                'tracking_id': interaction.get('tracking_id'),
                'zone_id': interaction.get('zone_id'),
                'type': interaction.get('interaction_type'),
                'duration': (datetime.utcnow() - interaction.get('start_time')).total_seconds() if interaction.get('start_time') else 0,
                'hand_position': interaction.get('hand_position'),
                'gesture': interaction.get('gesture_type')
            })
    except Exception as e:
        print(f"Error collecting interaction data: {e}")

    snapshot['active_interactions'] = active_interactions_data
    snapshot['interaction_count'] = len(active_interactions_data)
    snapshot['total_interactions_today'] = 0  # Would need cumulative counter

    # Gaze/Attention Data
    active_gaze_data = []
    gaze_fixation_count = 0

    try:
        # Would need gaze detector to expose active fixations
        # Placeholder for now
        pass
    except Exception as e:
        print(f"Error collecting gaze data: {e}")

    snapshot['active_gaze_events'] = active_gaze_data
    snapshot['gaze_fixation_count'] = gaze_fixation_count
    snapshot['total_gaze_events_today'] = 0  # Would need cumulative counter

    # AI Analysis (Gemini)
    snapshot['gemini_analysis_text'] = gemini_analysis_text

    if gemini_structured_data:
        scene = gemini_structured_data.get('scene', {})
        snapshot['crowd_density'] = scene.get('crowd_density')
        snapshot['energy_level'] = scene.get('energy_level')
        snapshot['dominant_activities'] = scene.get('dominant_activities', [])
        snapshot['scene_summary'] = scene.get('overall_summary')
        snapshot['anomalies_detected'] = scene.get('anomalies_detected', [])

        # Individual behaviors
        snapshot['individual_behaviors'] = gemini_structured_data.get('individuals', [])

        # Scene interactions
        snapshot['scene_interactions'] = gemini_structured_data.get('interactions', [])
    else:
        snapshot['crowd_density'] = None
        snapshot['energy_level'] = None
        snapshot['dominant_activities'] = []
        snapshot['scene_summary'] = None
        snapshot['anomalies_detected'] = []
        snapshot['individual_behaviors'] = []
        snapshot['scene_interactions'] = []

    # Events & Alerts
    active_events_data = []
    active_alerts_data = []

    try:
        if alert_manager:
            alerts = alert_manager.get_active_alerts()
            for alert in alerts:
                active_alerts_data.append({
                    'alert_id': alert.alert_id,
                    'priority': alert.priority.value if hasattr(alert.priority, 'value') else str(alert.priority),
                    'category': alert.category.value if hasattr(alert.category, 'value') else str(alert.category),
                    'message': alert.message,
                    'title': alert.title
                })
    except Exception as e:
        print(f"Error collecting alert data: {e}")

    snapshot['active_events'] = active_events_data
    snapshot['active_alerts'] = active_alerts_data
    snapshot['event_count'] = len(active_events_data)
    snapshot['alert_count'] = len(active_alerts_data)
    snapshot['critical_alert_count'] = sum(1 for alert in active_alerts_data if alert.get('priority') == 'critical')

    # Daily Counters (cumulative)
    snapshot['total_detections_today'] = 0  # Would need cumulative counter
    snapshot['total_sessions_today'] = 0  # Would need cumulative counter
    snapshot['total_alerts_today'] = 0  # Would need cumulative counter
    snapshot['total_events_today'] = 0  # Would need cumulative counter

    # ==================== PRODUCT INVENTORY DATA ====================
    snapshot.update(collect_product_metrics(
        product_detector=product_detector,
        product_interaction_tracker=product_interaction_tracker,
        zones_data=zones_data,
        db_session=db_session
    ))

    return snapshot


def collect_product_metrics(
    product_detector: Any = None,
    product_interaction_tracker: Any = None,
    zones_data: list = None,
    db_session: Any = None
) -> Dict[str, Any]:
    """
    Collect product inventory and interaction metrics

    Args:
        product_detector: ProductDetector instance
        product_interaction_tracker: ProductInteractionTracker instance
        zones_data: List of zones
        db_session: Database session

    Returns:
        Dictionary with product metrics
    """
    product_data = {
        'product_inventory': [],
        'total_products': 0,
        'active_product_interactions': [],
        'product_interaction_count': 0,
        'product_metrics': {},
        'total_product_views_today': 0,
        'total_product_touches_today': 0,
        'total_product_pickups_today': 0,
        'most_viewed_products': [],
        'most_interacted_products': []
    }

    if not product_detector or not db_session:
        return product_data

    try:
        # Collect product inventory from all zones
        inventory = []
        product_zones = [z for z in (zones_data or []) if z.get('type') == 'product' or z.get('zone_type') == 'product']

        for zone in product_zones:
            zone_id = zone.get('id')
            products = product_detector.get_products_in_zone(zone_id, db_session, use_cache=True)

            for product in products:
                inventory.append({
                    'id': product['id'],
                    'name': product['name'],
                    'category': product['category'],
                    'zone_id': product['zone_id'],
                    'zone_name': zone.get('name', 'Unknown'),
                    'position': product.get('position'),
                    'status': product.get('stock_status', 'in_stock')
                })

        product_data['product_inventory'] = inventory
        product_data['total_products'] = len(inventory)

        # Collect active product interactions
        if product_interaction_tracker:
            active_interactions = product_interaction_tracker.get_active_interactions()

            for interaction in active_interactions:
                product_data['active_product_interactions'].append({
                    'tracking_id': interaction.tracking_id,
                    'product_id': interaction.product_id,
                    'product_name': interaction.product_name,
                    'zone_id': interaction.zone_id,
                    'interaction_type': interaction.interaction_type,
                    'duration_seconds': interaction.duration_seconds,
                    'engagement_score': interaction.engagement_score,
                    'hand_position': {
                        'x': interaction.hand_position[0],
                        'y': interaction.hand_position[1]
                    } if interaction.hand_position else None,
                    'gesture_type': interaction.gesture_type
                })

            product_data['product_interaction_count'] = len(active_interactions)

        # Collect product engagement metrics from database
        try:
            from app.core.database import ProductEngagementMetrics, Product

            metrics_query = db_session.query(ProductEngagementMetrics).all()

            metrics_dict = {}
            total_views = 0
            total_touches = 0
            total_pickups = 0

            product_views = []  # For ranking most viewed
            product_interactions = []  # For ranking most interacted

            for metrics in metrics_query:
                product = db_session.query(Product).filter(Product.id == metrics.product_id).first()

                if product and product.is_active:
                    metrics_dict[metrics.product_id] = {
                        'views': metrics.total_views,
                        'touches': metrics.total_touches,
                        'pickups': metrics.total_pickups,
                        'avg_engagement_time': metrics.total_engagement_time_seconds / max(1, metrics.total_touches + metrics.total_pickups),
                        'purchase_intent_score': metrics.purchase_intent_score
                    }

                    # Accumulate totals
                    total_views += metrics.total_views
                    total_touches += metrics.total_touches
                    total_pickups += metrics.total_pickups

                    # For ranking
                    product_views.append({
                        'product_id': metrics.product_id,
                        'product_name': product.name,
                        'view_count': metrics.total_views
                    })

                    total_interactions = metrics.total_touches + metrics.total_pickups
                    product_interactions.append({
                        'product_id': metrics.product_id,
                        'product_name': product.name,
                        'interaction_count': total_interactions
                    })

            product_data['product_metrics'] = metrics_dict
            product_data['total_product_views_today'] = total_views
            product_data['total_product_touches_today'] = total_touches
            product_data['total_product_pickups_today'] = total_pickups

            # Top 5 most viewed and most interacted products
            product_views.sort(key=lambda x: x['view_count'], reverse=True)
            product_interactions.sort(key=lambda x: x['interaction_count'], reverse=True)

            product_data['most_viewed_products'] = product_views[:5]
            product_data['most_interacted_products'] = product_interactions[:5]

        except Exception as e:
            print(f"Error collecting product metrics from database: {e}")

    except Exception as e:
        print(f"Error in collect_product_metrics: {e}")
        import traceback
        traceback.print_exc()

    return product_data
