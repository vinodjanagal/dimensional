"""Arq worker entry point.

Run with:  arq app.jobs.worker.WorkerSettings

The worker is a separate process from the API. It connects to the same
Postgres and Redis, but serves no HTTP. It pulls jobs off the Redis
queue and runs the functions listed in `WorkerSettings.functions`.
"""

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.jobs.tasks import analyze_note


async def on_startup(ctx: dict) -> None:
    """Called once when the worker boots.

    Creates a database engine and session factory, and stashes it in
    `ctx` so every task invocation can open a session.
    """
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )
    ctx["db_engine"] = engine
    ctx["db_sessionmaker"] = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


async def on_shutdown(ctx: dict) -> None:
    """Called once when the worker shuts down. Disposes the engine."""
    engine = ctx.get("db_engine")
    if engine is not None:
        await engine.dispose()


class WorkerSettings:
    """Configuration consumed by the `arq` CLI."""

    functions = [analyze_note]

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    on_startup = on_startup
    on_shutdown = on_shutdown

    # If a job raises, retry up to this many times with exponential backoff.
    max_tries = 3

    # Keep result of finished jobs in Redis for 5 minutes. Our source of
    # truth is Postgres, so this is a small cache only.
    keep_result = 300