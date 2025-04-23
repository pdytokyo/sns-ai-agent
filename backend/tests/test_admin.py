import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_session
from backend.app.models import User, Client, JobLog
from backend.app.auth import get_password_hash

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

@pytest.fixture(name="test_admin")
def test_admin_fixture(session: Session):
    """Create a test admin user"""
    hashed_password = get_password_hash("admin123")
    admin = User(
        username="testadmin",
        email="admin@example.com",
        hashed_password=hashed_password,
        is_active=True,
        is_admin=True
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user"""
    hashed_password = get_password_hash("password123")
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture(name="test_client_data")
def test_client_data_fixture(session: Session, test_user: User):
    """Create test clients"""
    client1 = Client(
        name="Test Client 1",
        industry="Technology",
        user_id=test_user.id
    )
    client2 = Client(
        name="Test Client 2",
        industry="Healthcare",
        user_id=test_user.id
    )
    session.add(client1)
    session.add(client2)
    session.commit()
    session.refresh(client1)
    session.refresh(client2)
    return [client1, client2]

@pytest.fixture(name="test_job_logs")
def test_job_logs_fixture(session: Session, test_client_data: list, test_user: User):
    """Create test job logs"""
    job_logs = []
    
    for i in range(5):
        status = "success" if i < 3 else "failed"
        job_log = JobLog(
            job_type="video_processing",
            status=status,
            error_message="Test error" if status == "failed" else None,
            client_id=test_client_data[0].id,
            user_id=test_user.id
        )
        session.add(job_log)
        job_logs.append(job_log)
    
    for i in range(3):
        status = "success" if i < 2 else "failed"
        job_log = JobLog(
            job_type="script_generation",
            status=status,
            error_message="Test error" if status == "failed" else None,
            client_id=test_client_data[1].id,
            user_id=test_user.id
        )
        session.add(job_log)
        job_logs.append(job_log)
    
    for i in range(2):
        job_log = JobLog(
            job_type="system_task",
            status="success",
            user_id=test_user.id
        )
        session.add(job_log)
        job_logs.append(job_log)
    
    session.commit()
    for job_log in job_logs:
        session.refresh(job_log)
    
    return job_logs

@pytest.fixture(name="admin_headers")
def admin_headers_fixture(client: TestClient, test_admin: User):
    """Get authentication headers for admin user"""
    response = client.post(
        "/auth/login",
        data={
            "username": test_admin.username,
            "password": "admin123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_admin_stats_endpoint(client: TestClient, admin_headers: dict, test_job_logs: list):
    """Test the admin stats endpoint"""
    response = client.get("/admin/stats", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_jobs" in data
    assert "failed_jobs" in data
    assert "per_client" in data
    
    assert data["total_jobs"] == 10  # Total number of job logs
    assert data["failed_jobs"] == 3  # Number of failed job logs
    
    assert len(data["per_client"]) == 2  # Two clients with job logs
    
    client_stats = {str(k): v for k, v in data["per_client"].items()}
    
    client1_id = str(test_job_logs[0].client_id)
    assert client1_id in client_stats
    assert client_stats[client1_id]["total"] == 5
    assert client_stats[client1_id]["failed"] == 2
    
    client2_id = str(test_job_logs[5].client_id)
    assert client2_id in client_stats
    assert client_stats[client2_id]["total"] == 3
    assert client_stats[client2_id]["failed"] == 1

def test_admin_stats_unauthorized(client: TestClient, test_user: User):
    """Test that non-admin users cannot access the admin stats endpoint"""
    response = client.post(
        "/auth/login",
        data={
            "username": test_user.username,
            "password": "password123"
        }
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/admin/stats", headers=headers)
    
    assert response.status_code == 403
