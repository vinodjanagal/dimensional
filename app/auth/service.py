from sqlalchemy.orm import Session 
from fastapi import HTTPException

from app.models import User
from app.auth import repository
from app.auth import security

from pwdlib import PasswordHash
from app.auth.security import create_access_token, create_refresh_token


password_hash = PasswordHash.recommended()

def register_user(
        db: Session,
        email: str,
        password: str,
):
    existing_user = repository.get_user_by_email(db, email)

    if existing_user is not None:
        raise HTTPException(
            status_code = 400,
            detail= "Email already registered"

        )

    hashed_password = password_hash.hash(password)

    user = User(
        email=email,
        password_hash=hashed_password,
    )

    return repository.create_user(db, user)

def login_user(
        db:Session,
        email: str,
        password: str,
):
    user = repository.get_user_by_email(db, email)

    if user is None:
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


def refresh_access_token(db: Session, token: str):

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

    user = db.get(User, int(user_id))

    if user is None:
        raise HTTPException(
            status_code=401,
            detail= "User not found"
        )

    return security.create_access_token(user.id)

