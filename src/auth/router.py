import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.auth.deps import get_current_user
from src.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from src.auth.service import create_token, create_user, get_by_email, verify_password
from src.db import get_conn
from src.settings import JWT_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=JWT_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, response: Response, conn: asyncpg.Connection = Depends(get_conn)):
    if await get_by_email(conn, req.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = await create_user(conn, req.email, req.password)
    token = create_token(user["id"], user["email"])
    _set_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response, conn: asyncpg.Connection = Depends(get_conn)):
    user = await get_by_email(conn, req.email)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_token(user["id"], user["email"])
    _set_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: asyncpg.Record = Depends(get_current_user)):
    return dict(current_user)
