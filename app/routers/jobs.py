from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.core.database import get_db
from app.models import Job, Note, User
from app.repositories import job_repository
from app.schemas.job import JobEnqueuedResponse, JobResponse


router = APIRouter(tags=["Jobs"])


async def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool


async def _get_owned_note(
    db: AsyncSession, note_id: int, user: User
) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return note


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
    await _get_owned_note(db, note_id, user)

    job = Job(
        note_id=note_id,
        user_id=user.id,
        job_type="note_analysis",
        status="queued",
    )
    job = await job_repository.create(db, job)
    await db.commit()

    await arq.enqueue_job(
        "analyze_note",
        note_id=note_id,
        user_id=user.id,
        job_id=str(job.id),
    )

    return JobEnqueuedResponse(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = await job_repository.get_by_id(db, job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get("/notes/{note_id}/jobs", response_model=list[JobResponse])
async def list_jobs(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_owned_note(db, note_id, user)
    return await job_repository.list_for_note(db, note_id)