import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_session
from backend.app.models import User, Client, ClientCreate
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

@pytest.fixture(name="test_client_data")
def test_client_data_fixture():
    """Test client data"""
    return {
        "name": "Test Client",
        "industry": "Technology",
        "target_audience": {"age": "25-34", "interests": ["tech", "gadgets"]}
    }

@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    """Get authentication headers for test user"""
    response = client.post(
        "/auth/login",
        data={
            "username": test_user.username,
            "password": "password123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

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

def test_create_client(client: TestClient, auth_headers: dict, test_client_data: dict):
    """Test creating a client"""
    response = client.post(
        "/client/",
        json=test_client_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_client_data["name"]
    assert data["industry"] == test_client_data["industry"]
    assert data["target_audience"] == test_client_data["target_audience"]
    assert "id" in data
    assert "created_at" in data

def test_read_clients(client: TestClient, session: Session, auth_headers: dict, test_user: User):
    """Test reading all clients"""
    client1 = Client(name="Client 1", industry="Tech", user_id=test_user.id)
    client2 = Client(name="Client 2", industry="Finance", user_id=test_user.id)
    session.add(client1)
    session.add(client2)
    session.commit()
    
    response = client.get("/client/", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Client 1"
    assert data[1]["name"] == "Client 2"

def test_read_client(client: TestClient, session: Session, auth_headers: dict, test_user: User):
    """Test reading a specific client"""
    test_client = Client(name="Test Client", industry="Tech", user_id=test_user.id)
    session.add(test_client)
    session.commit()
    session.refresh(test_client)
    
    response = client.get(f"/client/{test_client.id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["industry"] == "Tech"
    assert data["id"] == test_client.id

def test_update_client(client: TestClient, session: Session, auth_headers: dict, test_user: User):
    """Test updating a client"""
    test_client = Client(name="Test Client", industry="Tech", user_id=test_user.id)
    session.add(test_client)
    session.commit()
    session.refresh(test_client)
    
    update_data = {
        "name": "Updated Client",
        "industry": "Healthcare",
        "target_audience": {"age": "35-44", "interests": ["health", "wellness"]}
    }
    
    response = client.put(
        f"/client/{test_client.id}",
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Client"
    assert data["industry"] == "Healthcare"
    assert data["target_audience"] == {"age": "35-44", "interests": ["health", "wellness"]}

def test_delete_client(client: TestClient, session: Session, admin_headers: dict, test_user: User):
    """Test deleting a client (admin only)"""
    test_client = Client(name="Test Client", industry="Tech", user_id=test_user.id)
    session.add(test_client)
    session.commit()
    session.refresh(test_client)
    
    response = client.delete(f"/client/{test_client.id}", headers=admin_headers)
    
    assert response.status_code == 204
    
    deleted_client = session.get(Client, test_client.id)
    assert deleted_client is None

def test_delete_client_unauthorized(client: TestClient, session: Session, auth_headers: dict, test_user: User):
    """Test deleting a client with non-admin user (should fail)"""
    test_client = Client(name="Test Client", industry="Tech", user_id=test_user.id)
    session.add(test_client)
    session.commit()
    session.refresh(test_client)
    
    response = client.delete(f"/client/{test_client.id}", headers=auth_headers)
    
    assert response.status_code == 403
    
    client_exists = session.get(Client, test_client.id)
    assert client_exists is not None

def test_read_client_unauthorized(client: TestClient, session: Session, auth_headers: dict, test_admin: User):
    """Test reading a client that belongs to another user (should fail for non-admin)"""
    test_client = Client(name="Admin Client", industry="Tech", user_id=test_admin.id)
    session.add(test_client)
    session.commit()
    session.refresh(test_client)
    
    response = client.get(f"/client/{test_client.id}", headers=auth_headers)
    
    assert response.status_code == 403

def test_admin_read_all_clients(client: TestClient, session: Session, admin_headers: dict, test_user: User, test_admin: User):
    """Test admin can read all clients regardless of owner"""
    client1 = Client(name="User Client", industry="Tech", user_id=test_user.id)
    client2 = Client(name="Admin Client", industry="Finance", user_id=test_admin.id)
    session.add(client1)
    session.add(client2)
    session.commit()
    
    response = client.get("/client/", headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    client_names = [c["name"] for c in data]
    assert "User Client" in client_names
    assert "Admin Client" in client_names
