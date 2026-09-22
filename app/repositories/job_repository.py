from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job


async def create(db: AsyncSession, job: Job) -> Job:
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def get_by_id(
    db: AsyncSession, job_id: UUID, user_id: int
) -> Job | None:
    """Fetch a job by ID, scoped to its owner.

    Returns None if the job does not exist OR belongs to another user,
    so callers cannot distinguish the two cases.
    """
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_for_note(
    db: AsyncSession, note_id: int, limit: int = 50
) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.note_id == note_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())