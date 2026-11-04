from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.job import JobEnqueuedResponse, JobResponse
from app.services import job_service


router = APIRouter(tags=["Jobs"])


async def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool


@router.post(
    "/notes/{note_id}/analyze",
    response_model=JobEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_analysis(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    arq: ArqRedis = Depends(get_arq_pool),
):
    job = await job_service.enqueue_analysis(db, note_id, user, arq)
    return JobEnqueuedResponse(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await job_service.get_job(db, job_id, user)


@router.get("/notes/{note_id}/jobs", response_model=list[JobResponse])
async def list_jobs(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await job_service.list_jobs_for_note(db, note_id, user)