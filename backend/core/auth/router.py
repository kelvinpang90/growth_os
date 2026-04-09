"""
Auth Router — register / login / refresh token / get current user
"""
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from core.i18n import t
from core.auth.repositories.user_repository import (
    create_user,
    delete_refresh_token,
    get_password_hash,
    get_refresh_token,
    get_user_by_email,
    get_user_by_email_or_username,
    get_user_full,
    get_user_simple,
    save_refresh_token,
    update_user,
)
from core.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
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

router = APIRouter(prefix="/api/auth", tags=["Auth — User Authentication"])
_bearer = HTTPBearer()


# ── 公开接口 ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             summary="Register")
async def register(req: RegisterRequest):
    # 创建新用户账号，注册成功后直接颁发 access/refresh token。
    existing = await get_user_by_email_or_username(req.email, req.username)
    if existing:
        raise HTTPException(status_code=400, detail=t("error.user_exists"))

    await create_user(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        platform=req.platform.value,
        language=req.language.value,
        currency=req.currency.value,
    )
    user = await get_user_simple(req.email)
    return await _issue_tokens(user["id"], user["username"], user["language"])


@router.post("/login", response_model=TokenResponse, summary="Login")
async def login(req: LoginRequest):
    # 验证邮箱和密码，通过后颁发 access/refresh token。
    user = await get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail=t("error.wrong_credentials"))

    return await _issue_tokens(user["id"], user["username"], user["language"])


@router.post("/refresh", response_model=TokenResponse, summary="Refresh Access Token")
async def refresh(req: RefreshRequest):
    # 使用有效的 refresh token 换取新的 access/refresh token（token 轮换）。
    token_hash = hash_refresh_token(req.refresh_token)
    record = await get_refresh_token(token_hash)
    if not record:
        raise HTTPException(status_code=401, detail=t("error.refresh_token_invalid"))

    if record["expires_at"] < datetime.now():
        await delete_refresh_token(token_hash)
        raise HTTPException(status_code=401, detail=t("error.refresh_token_expired"))

    # Token 轮换：删旧换新
    await delete_refresh_token(token_hash)
    return await _issue_tokens(record["user_id"], record["username"], record["language"])


@router.get("/me", response_model=UserResponse, summary="Get Current User")
async def me(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    # 解析 Bearer token 并返回当前登录用户的完整信息。
    user = await get_current_user(credentials.credentials)
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        platform=user["platform"],
        language=user["language"],
        currency=user["currency"],
        created_at=str(user["created_at"]),
    )


@router.patch("/me", response_model=UserResponse, summary="Update Current User")
async def update_me(
    req: UpdateUserRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    # 修改当前用户的密码、语言或货币设置。
    user = await get_current_user(credentials.credentials)

    if req.new_password:
        if not req.current_password:
            raise HTTPException(status_code=400, detail=t("error.current_password_required"))
        row = await get_password_hash(user["id"])
        if not verify_password(req.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail=t("error.wrong_current_password"))

    updates: dict = {}
    if req.new_password:
        updates["password_hash"] = hash_password(req.new_password)
    if req.language is not None:
        updates["language"] = req.language.value
    if req.currency is not None:
        updates["currency"] = req.currency.value

    if updates:
        await update_user(user["id"], updates)

    updated = await get_user_full(user["id"])
    return UserResponse(**{**dict(updated), "created_at": str(updated["created_at"])})


# ── 可复用的认证依赖 ──────────────────────────────────────────────────────

async def get_current_user(token: str) -> dict:
    # 从 JWT 中解析并验证用户信息，验证失败时抛出 401 异常。
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail=t("error.access_token_expired"))
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail=t("error.access_token_invalid"))

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail=t("error.token_type_error"))

    user = await get_user_full(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail=t("error.user_not_found"))
    return user


async def auth_required(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    # 路由级认证依赖，验证 Bearer token 并将当前用户对象注入路由函数。
    return await get_current_user(credentials.credentials)


# ── 内部工具 ──────────────────────────────────────────────────────────────

async def _issue_tokens(user_id: int, username: str, language: str = "en") -> TokenResponse:
    # 生成 access token 和 refresh token，并将 refresh token 哈希存入数据库。
    access_token = create_access_token(user_id, username, language)
    raw_refresh, refresh_hash = create_refresh_token()
    expires_at = datetime.now() + timedelta(days=settings.auth.refresh_token_expire_days)

    await save_refresh_token(user_id, refresh_hash, expires_at)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.auth.access_token_expire_minutes * 60,
    )
