from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.models import User
from app.auth.security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
):

    
    payload = decode_access_token(token)

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

    return user
   
