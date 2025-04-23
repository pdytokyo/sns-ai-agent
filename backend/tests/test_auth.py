import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_session
from backend.app.models import User, UserCreate

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

def test_register_user(client: TestClient, session: Session):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "is_active": True,
            "is_admin": False
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    
    user = session.get(User, data["id"])
    assert user is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.hashed_password != "password123"  # Password should be hashed

def test_register_duplicate_username(client: TestClient, session: Session):
    user = User(
        username="existinguser",
        email="existing@example.com",
        hashed_password="hashedpassword"
    )
    session.add(user)
    session.commit()
    
    response = client.post(
        "/auth/register",
        json={
            "username": "existinguser",
            "email": "new@example.com",
            "password": "password123",
            "is_active": True,
            "is_admin": False
        }
    )
    
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_login(client: TestClient, session: Session):
    from backend.app.auth import get_password_hash
    hashed_password = get_password_hash("password123")
    user = User(
        username="loginuser",
        email="login@example.com",
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    
    response = client.post(
        "/auth/login",
        data={
            "username": "loginuser",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient, session: Session):
    from backend.app.auth import get_password_hash
    hashed_password = get_password_hash("password123")
    user = User(
        username="loginuser2",
        email="login2@example.com",
        hashed_password=hashed_password
    )
    session.add(user)
    session.commit()
    
    response = client.post(
        "/auth/login",
        data={
            "username": "loginuser2",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]
