import os
import sys
import unittest
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.models import User, Client, Video, Post, Script, Report, JobLog, Token
from backend.app.database import engine
from sqlmodel import Session, select

class TestDatabaseSchema(unittest.TestCase):
    """Test the database schema to ensure all required tables exist."""
    
    def test_tables_exist(self):
        """Test that all required tables exist in the database."""
        from sqlmodel import SQLModel
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
                result = session.exec(select(model)).first()
                self.assertIsNone(result, f"Expected empty table for {table_name}")
    
    def test_job_log_table_columns(self):
        """Test that the job_log table has all required columns."""
        from sqlmodel import SQLModel
        SQLModel.metadata.create_all(engine)
        
        with Session(engine) as session:
            test_job = JobLog(
                job_type="test",
                status="success",
                error_message="No error",
                client_id=None,
                user_id=None
            )
            session.add(test_job)
            session.commit()
            
            session.refresh(test_job)
            
            self.assertIsNotNone(test_job.id)
            self.assertEqual(test_job.job_type, "test")
            self.assertEqual(test_job.status, "success")
            self.assertEqual(test_job.error_message, "No error")
            self.assertIsNone(test_job.client_id)
            self.assertIsNone(test_job.user_id)
            self.assertIsNotNone(test_job.created_at)

if __name__ == "__main__":
    unittest.main()
