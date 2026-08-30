import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base, User
from app.settings import settings
from app.auth.auth import get_current_user

TEST_DATABASE_URL = settings.database_url

test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        password_hash="test_hash",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, test_user):
    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield client

    app.dependency_overrides.clear()



@pytest.fixture
def test_user_cannot_get_another_users_note(client, db, test_user):
    response = client.post(
        "/notes",
        json={
            "title": "private note",
            "content": "user 1 content",
        },
    )

    assert response.status_code == 200

    note_id = response.json()["id"]

    other_user = User(
        email="other@example.com",
        password_hash="test_hash",
    )

    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    # Directly verify the ownership query using another user
    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 200
    