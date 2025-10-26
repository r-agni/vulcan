"""
Initialize new database tables for staff management and customer recognition
Run this script to add the new tables to your existing database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import Base, engine, SessionLocal
from app.database import (
    StaffMember, StaffLocation, AlertAssignment, StaffPerformanceMetrics,
    CustomerProfile, CustomerVisit, AppearanceMatch
)
from datetime import datetime

def init_new_tables():
    """Initialize the new tables"""
    print("=" * 60)
    print("  VideoAI Database Initialization")
    print("  Adding Staff Management & Customer Recognition Tables")
    print("=" * 60)
    print()

    try:
        # Create all tables (will only create missing ones)
        print("[1/3] Creating new database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
        print()

        # Add some sample staff members for testing
        print("[2/3] Adding sample staff members...")
        db = SessionLocal()

        # Check if staff already exists
        existing_staff = db.query(StaffMember).count()

        if existing_staff == 0:
            sample_staff = [
                StaffMember(
                    employee_id="EMP001",
                    name="Alice Johnson",
                    role="salesperson",
                    expertise_zones=[1, 2, 3],
                    is_on_duty=False,
                    notification_preferences={"websocket": True}
                ),
                StaffMember(
                    employee_id="EMP002",
                    name="Bob Smith",
                    role="salesperson",
                    expertise_zones=[4, 5],
                    is_on_duty=False,
                    notification_preferences={"websocket": True}
                ),
                StaffMember(
                    employee_id="MGR001",
                    name="Carol Martinez",
                    role="manager",
                    expertise_zones=[],
                    is_on_duty=False,
                    notification_preferences={"websocket": True}
                )
            ]

            for staff in sample_staff:
                db.add(staff)

            db.commit()
            print(f"✓ Added {len(sample_staff)} sample staff members")
        else:
            print(f"✓ {existing_staff} staff members already exist in database")

        print()
        print("[3/3] Verifying table structure...")

        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(engine)

        new_tables = [
            'staff_members',
            'staff_locations',
            'alert_assignments',
            'staff_performance_metrics',
            'customer_profiles',
            'customer_visits',
            'appearance_matches'
        ]

        for table_name in new_tables:
            if table_name in inspector.get_table_names():
                print(f"  ✓ {table_name}")
            else:
                print(f"  ✗ {table_name} - NOT FOUND")

        print()
        print("=" * 60)
        print("  Initialization Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Install new dependencies: pip install -r requirements.txt")
        print("2. Restart your application")
        print("3. Test staff clock-in API: POST /api/staff/clock-in?employee_id=EMP001")
        print("4. Monitor customer recognition in system logs")
        print()

        db.close()

    except Exception as e:
        print(f"\n✗ ERROR during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_new_tables()
