from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

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
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    return register_user(
        db, 
        user_data.email,
        user_data.password,
    )

@router.post("/login", response_model= TokenResponse)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):

    return login_user(
        db,
        user_data.email,
        user_data.password,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    user_data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    access_token = refresh_access_token(
        db,
        user_data.refresh_token,
    )

    return {
        "access_token": access_token,
    }