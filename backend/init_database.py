"""
Database initialization script for SNS AI Agent.
This script ensures all tables are created in the database.
"""

import os
import sys
from sqlmodel import SQLModel, create_engine, Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import User, Client, Video, Post, Script, Report, JobLog, Token
from app.database import engine

def init_database():
    """Initialize the database by creating all tables."""
    print("Initializing database...")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        tables = [
            ("users", User),
            ("clients", Client),
            ("videos", Video),
            ("posts", Post),
            ("scripts", Script),
            ("reports", Report),
            ("job_logs", JobLog),
            ("tokens", Token)
        ]
        
        for table_name, model in tables:
            try:
                session.query(model).first()
                print(f"✅ Table '{table_name}' exists and is accessible")
            except Exception as e:
                print(f"❌ Error accessing table '{table_name}': {str(e)}")
                raise

    print("Database initialization complete!")

if __name__ == "__main__":
    init_database()
