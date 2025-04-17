"""
Database initialization script to ensure all tables are created
"""
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import create_db_and_tables
from app.models import User, Client, Video, Post, Script, Report, JobLog

def init_database():
    """Initialize the database and create all tables"""
    print("Creating database tables...")
    create_db_and_tables()
    print("Database tables created successfully")

if __name__ == "__main__":
    init_database()
