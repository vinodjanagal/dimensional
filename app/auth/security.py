import jwt
from datetime import datetime, timedelta, timezone

from app.settings import settings

SECRET_KEY= settings.secret_key
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES= 30
REFRESH_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60

def create_access_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes= ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub" : str(user_id),
        "type" : "access",
        "exp" : expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

def create_refresh_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes= REFRESH_TOKEN_EXPIRE_MINUTES
    )


    payload = {
        "sub" : str(user_id),
        "type" : "refresh",
        "exp" : expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != "access":
            return None

        return payload

    except jwt.InvalidTokenError:
        return None


def decode_refresh_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        if payload.get("type") != "refresh":
            return None

        return payload

    except jwt.InvalidTokenError:
        return None