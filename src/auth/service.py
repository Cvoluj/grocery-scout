from datetime import datetime, timedelta, timezone

import asyncpg
import jwt
from passlib.context import CryptContext

from libs.pb_client import runtime
from src.settings import JWT_ALGORITHM, JWT_EXPIRE_MINUTES

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, runtime.get("JWT_SECRET"), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, runtime.get("JWT_SECRET"), algorithms=[JWT_ALGORITHM])


async def get_by_email(conn: asyncpg.Connection, email: str) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)


async def create_user(conn: asyncpg.Connection, email: str, password: str) -> asyncpg.Record:
    return await conn.fetchrow(
        "INSERT INTO users (email, hashed_password) VALUES ($1, $2) RETURNING id, email, created_at",
        email,
        hash_password(password),
    )
