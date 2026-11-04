import logging
import time
import uuid
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine, get_db
from app.core.logging import configure_logging, request_id_var
from app.routers import auth as auth_router
from app.routers import formulas as formulas_router
from app.routers import jobs as jobs_router
from app.routers import notes
from app.routers import quantities as quantities_router
from app.routers import units as units_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)

    logger.info(
        "api.starting",
        extra={
            "event": "api.starting",
            "db_pool_size": settings.db_pool_size,
            "db_max_overflow": settings.db_max_overflow,
        },
    )

    app.state.arq_pool = None

    try:
        app.state.arq_pool = await create_pool(
            RedisSettings.from_dsn(settings.redis_url)
        )
        yield
    finally:
        try:
            if app.state.arq_pool is not None:
                await app.state.arq_pool.close()
        finally:
            await engine.dispose()
            logger.info(
                "api.stopped",
                extra={"event": "api.stopped"},
            )


app = FastAPI(title="dimensional", lifespan=lifespan)


@app.get("/", tags=["ops"])
def root() -> dict[str, str]:
    return {"service": "dimensional", "status": "ok"}


@app.get("/healthz", tags=["ops"])
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/readyz", tags=["ops"])
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    # Session acquisition (Depends) runs before this body, so failure to
    # acquire surfaces as 500, not 503. Acceptable; revisit later.
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception(
            "readiness.database_failed",
            extra={"event": "readiness_check.database_failed"},
        )
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from None

    return {"status": "ready", "database": "connected"}


@app.middleware("http")
async def log_requests(request: Request, call_next):

    request_id = str(uuid.uuid4())
    request_id_token = request_id_var.set(request_id)
    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        logger.info(
            "http.request.started",
            extra={
                "event": "http.request.started",
                "method": request.method,
                "path": request.url.path,
            },
        )

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http.request.completed",
            extra={
                "event": "http.request.completed",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    except Exception:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.exception(
            "http.request.failed",
            extra={
                "event": "http.request.failed",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise

    finally:
        request_id_var.reset(request_id_token)


app.include_router(notes.router)
app.include_router(auth_router.router)
app.include_router(units_router.router)
app.include_router(quantities_router.router)
app.include_router(formulas_router.router)
app.include_router(jobs_router.router)
