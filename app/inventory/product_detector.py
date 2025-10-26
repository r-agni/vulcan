"""
Product Detector - Gemini-based product identification in zones
Analyzes video frames and identifies products visible in each zone
"""

import cv2
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.core.database import Product, ProductZoneMapping, ProductEngagementMetrics
from app.analytics.gemini_analyzer import GeminiAnalyzer


class ProductDetector:
    """
    Detect and catalog products using Gemini AI vision
    """

    def __init__(self, gemini_analyzer: GeminiAnalyzer):
        """
        Initialize product detector

        Args:
            gemini_analyzer: GeminiAnalyzer instance for AI-based detection
        """
        self.gemini_analyzer = gemini_analyzer
        self.product_cache = {}  # zone_id -> list of products

    def detect_products_in_zones(
        self,
        frame: any,
        zones: List[Dict],
        db: Session
    ) -> Dict[int, List[Dict]]:
        """
        Analyze frame and detect products in each product zone

        Args:
            frame: Video frame (numpy array)
            zones: List of zone dictionaries
            db: Database session

        Returns:
            Dictionary mapping zone_id to list of detected products
        """
        detected_products = {}

        # Filter to product zones only
        product_zones = [z for z in zones if z.get('type') == 'product' or z.get('zone_type') == 'product']

        for zone in product_zones:
            zone_id = zone.get('id')
            zone_name = zone.get('name', 'Unknown Zone')

            print(f"Detecting products in zone: {zone_name} (ID: {zone_id})")

            # Analyze this zone for products
            products = self._analyze_zone_for_products(frame, zone, db)

            if products:
                detected_products[zone_id] = products
                self.product_cache[zone_id] = products
                print(f"  ✓ Detected {len(products)} products in {zone_name}")

        return detected_products

    def _analyze_zone_for_products(
        self,
        frame: any,
        zone: Dict,
        db: Session
    ) -> List[Dict]:
        """
        Use Gemini to analyze a specific zone and identify products

        Args:
            frame: Video frame
            zone: Zone dictionary
            db: Database session

        Returns:
            List of detected product dictionaries
        """
        try:
            zone_id = zone.get('id')
            zone_name = zone.get('name', 'Unknown')
            zone_type = zone.get('zone_type', zone.get('type', 'product'))

            # Save frame temporarily
            import tempfile
            import os
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            cv2.imwrite(temp_file.name, frame)
            temp_file.close()

            # Call Gemini to identify products
            result = self.gemini_analyzer.analyze_products_in_zone(
                frame_path=temp_file.name,
                zone_name=zone_name,
                zone_type=zone_type
            )

            # Clean up temp file
            try:
                os.unlink(temp_file.name)
            except:
                pass

            if "error" in result:
                print(f"Error analyzing zone {zone_name}: {result['error']}")
                return []

            # Parse products from Gemini response
            products_data = result.get('products', [])

            # Save products to database
            saved_products = []
            for product_data in products_data:
                product = self._save_product_to_db(product_data, zone, db)
                if product:
                    saved_products.append({
                        'id': product.id,
                        'name': product.name,
                        'category': product.category,
                        'zone_id': zone_id,
                        'position': product_data.get('position'),
                        'confidence': product_data.get('confidence', 0.0)
                    })

            return saved_products

        except Exception as e:
            print(f"Error in _analyze_zone_for_products: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _save_product_to_db(
        self,
        product_data: Dict,
        zone: Dict,
        db: Session
    ) -> Optional[Product]:
        """
        Save detected product to database

        Args:
            product_data: Product information from Gemini
            zone: Zone dictionary
            db: Database session

        Returns:
            Product database record or None
        """
        try:
            product_name = product_data.get('name', 'Unknown Product')
            category = product_data.get('category', 'General')
            description = product_data.get('description', '')
            confidence = product_data.get('confidence', 0.0)
            position = product_data.get('position', {})

            # Check if product already exists in this zone
            existing = db.query(Product).filter(
                Product.name == product_name,
                Product.category == category
            ).first()

            if existing:
                # Update existing product
                product = existing
                product.gemini_description = description
                product.gemini_confidence = confidence
                product.updated_at = datetime.now(UTC)
            else:
                # Create new product
                product = Product(
                    name=product_name,
                    category=category,
                    description=description,
                    gemini_description=description,
                    gemini_confidence=confidence,
                    is_active=True
                )
                db.add(product)
                db.flush()  # Get product ID

                # Create engagement metrics record
                metrics = ProductEngagementMetrics(
                    product_id=product.id,
                    total_views=0,
                    total_touches=0,
                    total_pickups=0
                )
                db.add(metrics)

            # Create or update product zone mapping
            zone_id = zone.get('id')
            existing_mapping = db.query(ProductZoneMapping).filter(
                ProductZoneMapping.product_id == product.id,
                ProductZoneMapping.zone_id == zone_id
            ).first()

            if existing_mapping:
                # Update position
                existing_mapping.position_x = position.get('x')
                existing_mapping.position_y = position.get('y')
                existing_mapping.bounding_box = position.get('bounding_box')
                existing_mapping.last_verified = datetime.now(UTC)
            else:
                # Create new mapping
                mapping = ProductZoneMapping(
                    product_id=product.id,
                    zone_id=zone_id,
                    position_x=position.get('x'),
                    position_y=position.get('y'),
                    bounding_box=position.get('bounding_box'),
                    shelf_level=position.get('shelf_level'),
                    is_primary_location=True,
                    stock_status='in_stock'
                )
                db.add(mapping)

            db.commit()
            db.refresh(product)

            return product

        except Exception as e:
            db.rollback()
            print(f"Error saving product to database: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_products_in_zone(
        self,
        zone_id: int,
        db: Session,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Get list of products in a specific zone

        Args:
            zone_id: Zone ID
            db: Database session
            use_cache: Use cached data if available

        Returns:
            List of product dictionaries
        """
        # Check cache first
        if use_cache and zone_id in self.product_cache:
            return self.product_cache[zone_id]

        # Query from database
        try:
            mappings = db.query(ProductZoneMapping).filter(
                ProductZoneMapping.zone_id == zone_id,
                ProductZoneMapping.is_primary_location == True
            ).all()

            products = []
            for mapping in mappings:
                product = db.query(Product).filter(
                    Product.id == mapping.product_id,
                    Product.is_active == True
                ).first()

                if product:
                    products.append({
                        'id': product.id,
                        'name': product.name,
                        'category': product.category,
                        'zone_id': zone_id,
                        'position': {
                            'x': mapping.position_x,
                            'y': mapping.position_y,
                            'bounding_box': mapping.bounding_box
                        },
                        'shelf_level': mapping.shelf_level,
                        'stock_status': mapping.stock_status
                    })

            # Update cache
            self.product_cache[zone_id] = products

            return products

        except Exception as e:
            print(f"Error getting products from zone {zone_id}: {e}")
            return []

    def find_nearest_product(
        self,
        position: Tuple[float, float],
        zone_id: int,
        db: Session,
        max_distance: float = 0.15
    ) -> Optional[Dict]:
        """
        Find the nearest product to a given position within a zone

        Args:
            position: (x, y) normalized coordinates
            zone_id: Zone ID
            db: Database session
            max_distance: Maximum distance threshold

        Returns:
            Product dictionary or None
        """
        products = self.get_products_in_zone(zone_id, db)

        nearest_product = None
        min_distance = float('inf')

        for product in products:
            prod_pos = product.get('position', {})
            prod_x = prod_pos.get('x')
            prod_y = prod_pos.get('y')

            if prod_x is None or prod_y is None:
                continue

            # Calculate Euclidean distance
            distance = ((position[0] - prod_x) ** 2 + (position[1] - prod_y) ** 2) ** 0.5

            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                nearest_product = product.copy()
                nearest_product['distance'] = distance

        return nearest_product

    def get_product_by_id(self, product_id: int, db: Session) -> Optional[Product]:
        """
        Get product by ID

        Args:
            product_id: Product ID
            db: Database session

        Returns:
            Product record or None
        """
        try:
            return db.query(Product).filter(Product.id == product_id).first()
        except Exception as e:
            print(f"Error getting product {product_id}: {e}")
            return None

    def get_all_products(self, db: Session, active_only: bool = True) -> List[Product]:
        """
        Get all products from database

        Args:
            db: Database session
            active_only: Return only active products

        Returns:
            List of Product records
        """
        try:
            query = db.query(Product)
            if active_only:
                query = query.filter(Product.is_active == True)
            return query.all()
        except Exception as e:
            print(f"Error getting all products: {e}")
            return []

    def clear_cache(self):
        """Clear the product cache"""
        self.product_cache.clear()
