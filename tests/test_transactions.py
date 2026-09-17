import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, User, Note
from app.core.config import settings
from sqlalchemy import select


@pytest.mark.asyncio
async def test_flush_then_rollback(db):
    user = User(
        email="transaction@test.com",
        password_hash="test_hash",
    )

    db.add(user)
    await db.flush()

    assert user.id is not None

    await db.rollback()

    result = await db.execute(select(User).where(User.id == user.id))
    found = result.scalar_one_or_none()
    assert found is None

@pytest.mark.asyncio
async def test_flush_then_commit_persists(db):
    user = User(
        email="commit@test.com",
        password_hash="test_hash",
    )

    db.add(user)
    await db.flush()

    assert user.id is not None

    await db.commit()

    result = await db.execute(select(User).where(User.id == user.id))
    found = result.scalar_one_or_none()

    assert found is not None
    assert found.email == "commit@test.com"

@pytest.mark.asyncio
async def test_rollback_undoes_multiple_operations(db):
    user = User(
        email="multi@test.com",
        password_hash="test_hash",
    )

    db.add(user)
    await db.flush()

    note = Note(
        owner_id=user.id,
        title="Test",
        content="Should be rolled back",
    )

    db.add(note)
    await db.flush()

    assert user.id is not None
    assert note.id is not None

    await db.rollback()


    result = await db.execute(select(User).where(User.id == user.id))
    saved_user = result.scalar_one_or_none()

    found = await db.execute(select(Note).where(Note.id == note.id))
    saved_note = found.scalar_one_or_none()

    assert saved_user is None
    assert saved_note is None
