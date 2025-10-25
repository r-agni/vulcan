#!/usr/bin/env python3
"""
Clear all data from the database
"""

import sys
import os
from sqlalchemy import text

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import SessionLocal, init_db, Base, engine
from app.database import (
    Person, DetectionEvent, BehaviorAnalysis,
    Zone, PersonTrajectory, DwellTimeRecord, VirtualLine,
    LineCrossingEvent, OccupancyLog, QueueMetrics,
    HeatmapData, ProductInteraction
)


def clear_all_data():
    """Delete all data from all tables"""
    print("Clearing all data from database...")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Get counts before deletion
        print("\nData before clearing:")
        print(f"  Persons: {db.query(Person).count()}")
        print(f"  Detection Events: {db.query(DetectionEvent).count()}")
        print(f"  Behavior Analyses: {db.query(BehaviorAnalysis).count()}")
        print(f"  Zones: {db.query(Zone).count()}")
        print(f"  Person Trajectories: {db.query(PersonTrajectory).count()}")
        print(f"  Dwell Time Records: {db.query(DwellTimeRecord).count()}")
        print(f"  Virtual Lines: {db.query(VirtualLine).count()}")
        print(f"  Line Crossing Events: {db.query(LineCrossingEvent).count()}")
        print(f"  Occupancy Logs: {db.query(OccupancyLog).count()}")
        print(f"  Queue Metrics: {db.query(QueueMetrics).count()}")
        print(f"  Heatmap Data: {db.query(HeatmapData).count()}")
        print(f"  Product Interactions: {db.query(ProductInteraction).count()}")

        print("\n" + "=" * 60)
        print("Deleting all records...")
        print("=" * 60)

        # Delete in order to respect foreign key constraints
        # Delete child records first
        deleted_counts = {}

        deleted_counts['Product Interactions'] = db.query(ProductInteraction).delete()
        deleted_counts['Heatmap Data'] = db.query(HeatmapData).delete()
        deleted_counts['Queue Metrics'] = db.query(QueueMetrics).delete()
        deleted_counts['Occupancy Logs'] = db.query(OccupancyLog).delete()
        deleted_counts['Line Crossing Events'] = db.query(LineCrossingEvent).delete()
        deleted_counts['Dwell Time Records'] = db.query(DwellTimeRecord).delete()
        deleted_counts['Person Trajectories'] = db.query(PersonTrajectory).delete()
        deleted_counts['Behavior Analyses'] = db.query(BehaviorAnalysis).delete()
        deleted_counts['Detection Events'] = db.query(DetectionEvent).delete()

        # Delete parent records
        deleted_counts['Virtual Lines'] = db.query(VirtualLine).delete()
        deleted_counts['Zones'] = db.query(Zone).delete()
        deleted_counts['Persons'] = db.query(Person).delete()

        # Commit all deletions
        db.commit()

        print("\nRecords deleted:")
        for table, count in deleted_counts.items():
            if count > 0:
                print(f"  {table}: {count}")

        # Verify all tables are empty
        print("\n" + "=" * 60)
        print("Verification - Data after clearing:")
        print(f"  Persons: {db.query(Person).count()}")
        print(f"  Detection Events: {db.query(DetectionEvent).count()}")
        print(f"  Behavior Analyses: {db.query(BehaviorAnalysis).count()}")
        print(f"  Zones: {db.query(Zone).count()}")
        print(f"  Person Trajectories: {db.query(PersonTrajectory).count()}")
        print(f"  Dwell Time Records: {db.query(DwellTimeRecord).count()}")
        print(f"  Virtual Lines: {db.query(VirtualLine).count()}")
        print(f"  Line Crossing Events: {db.query(LineCrossingEvent).count()}")
        print(f"  Occupancy Logs: {db.query(OccupancyLog).count()}")
        print(f"  Queue Metrics: {db.query(QueueMetrics).count()}")
        print(f"  Heatmap Data: {db.query(HeatmapData).count()}")
        print(f"  Product Interactions: {db.query(ProductInteraction).count()}")

        print("\n" + "=" * 60)
        print("Database cleared successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError clearing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def reset_database():
    """Drop all tables and recreate them (nuclear option)"""
    print("RESETTING DATABASE (dropping and recreating all tables)...")
    print("=" * 60)

    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped")

        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        print("All tables recreated")

        print("\n" + "=" * 60)
        print("Database reset successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError resetting database: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clear or reset the database")
    parser.add_argument('--reset', action='store_true',
                       help='Drop and recreate all tables (use with caution!)')

    args = parser.parse_args()

    if args.reset:
        confirm = input("Are you sure you want to RESET the entire database? This will drop all tables. (yes/no): ")
        if confirm.lower() == 'yes':
            reset_database()
        else:
            print("Reset cancelled")
    else:
        confirm = input("Are you sure you want to clear all data from the database? (yes/no): ")
        if confirm.lower() == 'yes':
            clear_all_data()
        else:
            print("Clear cancelled")
