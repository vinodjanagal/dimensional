"""Job service — owns the transaction boundary for job enqueue + lifecycle."""

from uuid import UUID

from arq import ArqRedis
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, User
from app.repositories import job_repository
from app.auth.permissions import get_owned_note as _get_owned_note


async def enqueue_analysis(
    db: AsyncSession,
    note_id: int,
    user: User,
    arq: ArqRedis,
) -> Job:
    """Create a Job row and enqueue it. Atomic: either both happen or neither."""

    await _get_owned_note(db, note_id, user)

    job = Job(
        note_id=note_id,
        user_id=user.id,
        job_type="note_analysis",
        status="queued",
    )
    db.add(job)
    await db.flush()                  # assigns job.id, does NOT commit

    try:
        await arq.enqueue_job(
            "analyze_note",
            note_id=note_id,
            user_id=user.id,
            job_id=str(job.id),
        )
    except Exception as exc:
        await db.rollback()           # discard the un-committed Job row
        raise HTTPException(
            status_code=503,
            detail="Job queue unavailable, please retry",
        ) from exc

    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: UUID, user: User) -> Job:
    job = await job_repository.get_by_id(db, job_id, user.id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


async def list_jobs_for_note(
    db: AsyncSession, note_id: int, user: User
) -> list[Job]:
    await _get_owned_note(db, note_id, user)
    return await job_repository.list_for_note(db, note_id)