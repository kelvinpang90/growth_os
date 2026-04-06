"""
Auth 路由 — 注册 / 登录 / 刷新 Token / 获取当前用户
"""
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from core.database import execute, fetchone
from core.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from core.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Auth — 用户认证"])
_bearer = HTTPBearer()


# ── 公开接口 ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             summary="用户注册")
async def register(req: RegisterRequest):
    existing = await fetchone(
        "SELECT id FROM users WHERE email = :email OR username = :username",
        {"email": req.email, "username": req.username},
    )
    if existing:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    await execute(
        """
        INSERT INTO users (username, email, password_hash, platform)
        VALUES (:username, :email, :password_hash, :platform)
        """,
        {
            "username": req.username,
            "email": req.email,
            "password_hash": hash_password(req.password),
            "platform": req.platform.value,
        },
    )
    user = await fetchone(
        "SELECT id, username FROM users WHERE email = :email",
        {"email": req.email},
    )
    return await _issue_tokens(user["id"], user["username"])


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(req: LoginRequest):
    user = await fetchone(
        "SELECT id, username, password_hash FROM users WHERE email = :email AND is_active = 1",
        {"email": req.email},
    )
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    return await _issue_tokens(user["id"], user["username"])


@router.post("/refresh", response_model=TokenResponse, summary="刷新 Access Token")
async def refresh(req: RefreshRequest):
    token_hash = hash_refresh_token(req.refresh_token)
    record = await fetchone(
        """
        SELECT rt.user_id, rt.expires_at, u.username
        FROM refresh_tokens rt
        JOIN users u ON u.id = rt.user_id
        WHERE rt.token_hash = :token_hash AND u.is_active = 1
        """,
        {"token_hash": token_hash},
    )
    if not record:
        raise HTTPException(status_code=401, detail="Refresh token 无效")

    if record["expires_at"] < datetime.utcnow():
        await execute(
            "DELETE FROM refresh_tokens WHERE token_hash = :h",
            {"h": token_hash},
        )
        raise HTTPException(status_code=401, detail="Refresh token 已过期")

    # Token 轮换：删旧换新
    await execute("DELETE FROM refresh_tokens WHERE token_hash = :h", {"h": token_hash})
    return await _issue_tokens(record["user_id"], record["username"])


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def me(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    user = await get_current_user(credentials.credentials)
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        platform=user["platform"],
        created_at=str(user["created_at"]),
    )


# ── 可复用的认证依赖 ──────────────────────────────────────────────────────

async def get_current_user(token: str) -> dict:
    """FastAPI Depends 依赖，其他路由保护用：
        user = Depends(auth_required)
    """
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Access token 无效")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token 类型错误")

    user = await fetchone(
        "SELECT id, username, email, platform, created_at FROM users WHERE id = :id AND is_active = 1",
        {"id": int(payload["sub"])},
    )
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


async def auth_required(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """路由级保护依赖，直接注入用户对象：
        @router.get("/protected")
        async def protected(user: dict = Depends(auth_required)):
            ...
    """
    return await get_current_user(credentials.credentials)


# ── 内部工具 ──────────────────────────────────────────────────────────────

async def _issue_tokens(user_id: int, username: str) -> TokenResponse:
    access_token = create_access_token(user_id, username)
    raw_refresh, refresh_hash = create_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.auth.refresh_token_expire_days)

    await execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES (:user_id, :token_hash, :expires_at)
        """,
        {"user_id": user_id, "token_hash": refresh_hash, "expires_at": expires_at},
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.auth.access_token_expire_minutes * 60,
    )
