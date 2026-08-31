import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, User, Note
from app.settings import settings


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


def test_flush_then_rollback(db):
    user = User(
        email="transaction@test.com",
        password_hash="test_hash",
    )

    db.add(user)
    db.flush()

    assert user.id is not None

    db.rollback()

    result = db.query(User).filter(User.id == user.id).first()

    assert result is None


def test_flush_then_commit_persists(db):
    user = User(
        email="commit@test.com",
        password_hash="test_hash",
    )

    db.add(user)
    db.flush()

    assert user.id is not None

    db.commit()

    result = db.query(User).filter(User.id == user.id).first()

    assert result is not None
    assert result.email == "commit@test.com"


def test_rollback_undoes_multiple_operations(db):
    user = User(
        email="multi@test.com",
        password_hash="test_hash",
    )

    db.add(user)
    db.flush()

    note = Note(
        owner_id=user.id,
        title="Test",
        content="Should be rolled back",
    )

    db.add(note)
    db.flush()

    assert user.id is not None
    assert note.id is not None

    db.rollback()

    saved_user = db.query(User).filter(User.id == user.id).first()
    saved_note = db.query(Note).filter(Note.id == note.id).first()

    assert saved_user is None
    assert saved_note is None