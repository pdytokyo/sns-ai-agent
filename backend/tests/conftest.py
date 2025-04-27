import os
import pytest
import sys
import tempfile
import types
import openai
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

from backend.app import database
database.engine = test_engine

@pytest.fixture(autouse=True)
def _mock_openai(monkeypatch):
    """
    Mock OpenAI API calls to avoid actual API calls during tests
    """
    def _fake_create(**kw):
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(
                        content="This is a test script generated based on the pattern."
                    )
                )
            ]
        )
    
    monkeypatch.setattr(openai.ChatCompletion, "create", _fake_create)
    
    def _fake_chat_create(*args, **kwargs):
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(
                        content="This is a test script generated based on the pattern."
                    )
                )
            ]
        )
    
    if hasattr(openai, "OpenAI"):
        original_init = openai.OpenAI.__init__
        
        def patched_init(self, *args, **kwargs):
            result = original_init(self, *args, **kwargs)
            self.chat.completions.create = _fake_chat_create
            return result
        
        monkeypatch.setattr(openai.OpenAI, "__init__", patched_init)
        
    try:
        from backend.app.services.script_generator import ScriptGenerator
        
        async def _fake_generate_script(self, pattern, client_info):
            return {
                "script": "This is a test script generated based on the pattern.",
                "template_path": "data/templates/1.txt",
                "template_distance": 0.1,
                "char_counts": {"0": 10, "3": 15, "6": 12},
                "time_codes": {"0": 0, "3": 3, "6": 6}
            }
        
        monkeypatch.setattr(ScriptGenerator, "generate_script", _fake_generate_script)
    except ImportError:
        pass  # Module might not be available in all test contexts

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
