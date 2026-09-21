from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Formula


async def list_for_note(db: AsyncSession, note_id: int) -> list[Formula]:
    result = await db.execute(
        select(Formula)
        .where(Formula.note_id == note_id)
        .order_by(Formula.created_at.desc())
    )
    return list(result.scalars().all())


async def get_by_name(
    db: AsyncSession, note_id: int, name: str
) -> Formula | None:
    result = await db.execute(
        select(Formula).where(
            Formula.note_id == note_id,
            Formula.name == name,
        )
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, formula: Formula) -> Formula:
    db.add(formula)
    await db.flush()
    await db.refresh(formula)
    return formula