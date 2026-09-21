from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Quantity


async def list_for_note(db: AsyncSession, note_id: int) -> list[Quantity]:
    result = await db.execute(
        select(Quantity)
        .where(Quantity.note_id == note_id)
        .order_by(Quantity.created_at.desc())
    )
    return list(result.scalars().all())


async def create(db: AsyncSession, quantity: Quantity) -> Quantity:
    db.add(quantity)
    await db.flush()
    await db.refresh(quantity)
    return quantity