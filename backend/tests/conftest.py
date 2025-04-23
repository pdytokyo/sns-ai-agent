import os
import pytest
import sys
import tempfile
from pathlib import Path
from sqlmodel import SQLModel, create_engine
from alembic.config import Config
from alembic import command

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

TEST_DB_PATH = tempfile.gettempdir() + "/test_app.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"

test_engine = create_engine(TEST_DB_URL)

import backend.app.database
backend.app.database.engine = test_engine

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Set up the test database with all tables and run migrations
    This fixture runs automatically before any tests
    """
    Path(TEST_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)
    
    SQLModel.metadata.create_all(test_engine)
    
    # Run Alembic migrations
    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Warning: Alembic migration failed: {e}")
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)
