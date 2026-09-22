import asyncio
import sys


import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base, User
from app.auth.auth import get_current_user
from app.routers.jobs import get_arq_pool

if sys.platform == "win32":
    # psycopg (async) requires a SelectorEventLoop on Windows.
    # The default ProactorEventLoop does not support the socket
    # primitives async SQLAlchemy relies on.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URL = settings.test_database_url

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine, autoflush=False, expire_on_commit=False
)

@pytest_asyncio.fixture
async def db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        from scripts.seed_units import seed_units
        await seed_units(session)
        await session.commit()
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(db):
    user = User(email="test@example.com", password_hash="test_hash")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(client, test_user):
    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()


class FakeArqPool:
    """Test double for the Arq Redis pool.

    Records enqueued jobs and returns None (the real pool returns an
    ArqJob object, which tests do not need).
    """

    def __init__(self):
        self.enqueued: list[tuple[str, dict]] = []

    async def enqueue_job(self, function: str, **kwargs):
        self.enqueued.append((function, kwargs))
        return None


@pytest_asyncio.fixture
async def fake_arq():
    """Return a FakeArqPool and register it as a dependency override."""
    pool = FakeArqPool()

    async def override():
        return pool

    app.dependency_overrides[get_arq_pool] = override
    yield pool
    app.dependency_overrides.pop(get_arq_pool, None)