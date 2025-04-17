import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import JobLog, JobLogCreate, User, Client

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_job_log(session: Session):
    """Test creating a job log entry"""
    job_log = JobLog(
        job_type="video_processing",
        status="failed",
        error_message="Test error message"
    )
    session.add(job_log)
    session.commit()
    session.refresh(job_log)
    
    assert job_log.id is not None
    assert job_log.job_type == "video_processing"
    assert job_log.status == "failed"
    assert job_log.error_message == "Test error message"
    assert job_log.created_at is not None

def test_job_log_with_client(session: Session):
    """Test creating a job log entry with client reference"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashedpassword"
    )
    session.add(user)
    session.commit()
    
    client = Client(
        name="Test Client",
        industry="Technology",
        user_id=user.id
    )
    session.add(client)
    session.commit()
    
    job_log = JobLog(
        job_type="script_generation",
        status="failed",
        error_message="Client-related error",
        client_id=client.id
    )
    session.add(job_log)
    session.commit()
    session.refresh(job_log)
    
    assert job_log.id is not None
    assert job_log.client_id == client.id
    assert job_log.client.name == "Test Client"

def test_job_log_with_user(session: Session):
    """Test creating a job log entry with user reference"""
    user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password="hashedpassword"
    )
    session.add(user)
    session.commit()
    
    job_log = JobLog(
        job_type="user_action",
        status="failed",
        error_message="User-related error",
        user_id=user.id
    )
    session.add(job_log)
    session.commit()
    session.refresh(job_log)
    
    assert job_log.id is not None
    assert job_log.user_id == user.id
    assert job_log.user.username == "testuser2"
