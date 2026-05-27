import asyncpg
import jwt
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.service import decode_token, get_by_email
from src.db import get_conn

_bearer = HTTPBearer()


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    conn: asyncpg.Connection = Depends(get_conn),
) -> asyncpg.Record:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(access_token)
        email: str = payload["email"]
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await get_by_email(conn, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def require_page_auth(access_token: str | None = Cookie(default=None)) -> None:
    if not access_token:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    try:
        decode_token(access_token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
