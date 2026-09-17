from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.auth.schemas import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    AccessTokenResponse

)

from app.auth.service import (
    register_user,
    login_user,
    refresh_access_token,
)


router = APIRouter(
    prefix= "/auth",
    tags=["Authentication"]
)

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    return await register_user(
        db, 
        user_data.email,
        user_data.password,
    )

@router.post("/login", response_model= TokenResponse)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):

    return await login_user(
        db,
        user_data.email,
        user_data.password,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    user_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    access_token = await refresh_access_token(
        db,
        user_data.refresh_token,
    )

    return {
        "access_token": access_token,
    }
