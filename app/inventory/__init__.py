"""
Product Inventory Management System
Tracks products, detects them using Gemini AI, and monitors interactions
"""

from .product_detector import ProductDetector
from .product_interaction_tracker import ProductInteractionTracker

__all__ = [
    "ProductDetector",
    "ProductInteractionTracker",
]
