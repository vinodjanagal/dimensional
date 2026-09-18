from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Unit


async def get_by_symbol(db: AsyncSession, symbol: str) -> Unit | None:
    result = await db.execute(select(Unit).where(Unit.symbol == symbol))
    return result.scalar_one_or_none()


async def list_all(db: AsyncSession) -> list[Unit]:
    result = await db.execute(select(Unit).order_by(Unit.symbol))
    return list(result.scalars().all())