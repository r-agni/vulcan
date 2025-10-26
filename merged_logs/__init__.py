"""
Merged Logs Module
Provides simplified 2-table data storage for all video analytics
"""

from .database import Base, Users, CameraRoom, engine, SessionLocal, init_merged_db
from .aggregator import collect_analytics_snapshot
from .logger import MergedLogger

__all__ = [
    'Base',
    'Users',
    'CameraRoom',
    'engine',
    'SessionLocal',
    'init_merged_db',
    'collect_analytics_snapshot',
    'MergedLogger'
]
