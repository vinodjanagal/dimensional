from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from sqlalchemy import select


async def get_user_by_email(db: AsyncSession, email: str):
    result= await db.execute(
        select(User).where
        (User.email == email)
    )

    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: User):
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


