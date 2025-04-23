"""
Test script to verify database migration functionality
"""
import os
import sqlite3
import logging
from dotenv import load_dotenv
import sys
from alembic.config import Config
from alembic import command

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "dummy_key_for_testing"
    logging.info("Set dummy OPENAI_API_KEY for testing")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.database import engine
from sqlmodel import SQLModel

DB_PATH = "backend/data/app.db"

if os.path.exists(DB_PATH):
    logging.info(f"Existing database found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(clients)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    conn.close()
    
    if 'industry' in columns:
        logging.info("'industry' column already exists in clients table")
    else:
        logging.info("'industry' column missing from clients table, will be added by migration")
else:
    logging.info(f"No existing database found at {DB_PATH}, will create new one")

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")

SQLModel.metadata.create_all(engine)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(clients)")
columns = {row[1]: row[2] for row in cursor.fetchall()}
conn.close()

if 'industry' in columns:
    logging.info("Migration successful: 'industry' column exists in clients table")
    print("Database migration successful")
else:
    logging.error("Migration failed: 'industry' column still missing from clients table")
    print("Database migration failed")
