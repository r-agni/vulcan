"""
Initialize the database with all required tables
"""
from app.core.database import init_db

if __name__ == "__main__":
    print("Initializing database tables...")
    init_db()
    print("✓ Database tables created successfully!")
