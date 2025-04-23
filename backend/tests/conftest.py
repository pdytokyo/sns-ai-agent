import os
import pytest
import sys
from sqlmodel import SQLModel
from alembic.config import Config
from alembic import command

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database import engine

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Set up the test database with all tables and run migrations
    This fixture runs automatically before any tests
    """
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    
    SQLModel.metadata.create_all(engine)
    
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    
    yield
