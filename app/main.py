import logging
import time
import uuid
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.routers import notes
from app.routers import auth as auth_router
from app.routers import units as units_router
from app.routers import formulas as formulas_router
from app.routers import quantities as quantities_router

app = FastAPI(title="Notes API")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(
    f"Starting API with DB_POOL_SIZE={settings.db_pool_size}, "
    f"DB_MAX_OVERFLOW={settings.db_max_overflow}"
)


@app.get("/")
def root():
    return {"message": "notes api is running"}


app.include_router(notes.router)
app.include_router(auth_router.router)
app.include_router(units_router.router)
app.include_router(quantities_router.router)
app.include_router(formulas_router.router)

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(f"Started {request.method} {request.url.path} [Request-ID: {request_id}]")

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f"Completed {request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"[Request-ID: {request_id}] in {process_time:.4f}s"
    )
    response.headers["X-Request-ID"] = request_id
    return response
