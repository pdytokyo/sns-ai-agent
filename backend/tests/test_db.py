import os
import sys
import unittest
import sqlite3
from pathlib import Path

from sqlmodel import Session, select, SQLModel, create_engine

test_engine = create_engine("sqlite:///:memory:")

from backend.app.models import User, Client, Video, Post, Script, Report, JobLog, Token

SQLModel.metadata.create_all(test_engine)

class TestDatabaseSchema(unittest.TestCase):
    """Test the database schema to ensure all required tables exist."""
    
    def test_tables_exist(self):
        """Test that all required tables exist in the database."""
        with Session(test_engine) as session:
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
    
    def test_job_log_table_columns(self):
        """Test that the job_log table has all required columns."""
        with Session(test_engine) as session:
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
