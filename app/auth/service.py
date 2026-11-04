from pydantic import EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession 
from fastapi import HTTPException

from app.models import User
from app.auth import repository, security

from pwdlib import PasswordHash
from app.auth.security import create_access_token, create_refresh_token


password_hash = PasswordHash.recommended()

# Pre-computed once at import - used for constant-time dummy verification
_Dummy_HASH = password_hash.hash("__dummy_password_for_timing__")

async def register_user(
        db: AsyncSession,
        email: EmailStr,
        password: str = Field(min_length=8, max_length=128),
):
    try:
        existing_user = await repository.get_user_by_email(db, email)

        if existing_user is not None:
            raise HTTPException(
                status_code = 409,
                detail= "Email already registered"

            )

        user = User(
            email=email,
            password_hash=password_hash.hash(password),
        )

        user =  await repository.create_user(db, user)

        await db.commit()

        return user

    except IntegrityError as e:
        await db.rollback()
        # Race: another request inserted the same email between our check and our insert.
        # DB unique constraint is the source of truth.
        raise HTTPException(status_code=409, detail="Email already registered") from e

    except Exception:
        await db.rollback()
        raise
   

async def login_user(
        db:AsyncSession,
        email: EmailStr,
        password: str,
):
    DUMMY_HASH = password_hash.hash("dummy")  # module-level, once

    user = await repository.get_user_by_email(db, email)

    if user is None:
        password_hash.verify(password, DUMMY_HASH) # burn the same time
        raise HTTPException(
            status_code= 401,
            detail="Invalid email or password",
        )

    if not password_hash.verify(password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail= "Invalid email or password"
        )

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
    }


async def refresh_access_token(db: AsyncSession, token: str):

    payload = security.decode_refresh_token(token)

    if payload is None:
        raise HTTPException(
            status_code = 401,
            detail= "Invalid or expired token",
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code = 401,
            detail= "Invalid token"
        )

    user = await db.get(User, int(user_id))

    if user is None:
        raise HTTPException(
            status_code=401,
            detail= "User not found"
        )

    return security.create_access_token(user.id)

