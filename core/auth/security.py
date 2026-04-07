import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    # 使用 bcrypt 对明文密码进行哈希处理。
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    # 验证明文密码与哈希值是否匹配。
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, username: str, language: str = "en") -> str:
    # 生成包含用户 ID、用户名和语言偏好的 JWT access token。
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.auth.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "username": username,
        "language": language,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.auth.jwt_secret, algorithm=settings.auth.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    # 解码并验证 JWT access token，返回 payload 字典。
    return jwt.decode(
        token,
        settings.auth.jwt_secret,
        algorithms=[settings.auth.jwt_algorithm],
    )


def create_refresh_token() -> tuple[str, str]:
    # 生成随机 refresh token，返回 (明文, SHA-256 哈希) 元组，数据库只存哈希。
    raw = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw)
    return raw, token_hash


def hash_refresh_token(raw: str) -> str:
    # 对明文 refresh token 进行 SHA-256 哈希，供数据库查询使用。
    return _hash_token(raw)


def _hash_token(raw: str) -> str:
    # 计算字符串的 SHA-256 十六进制摘要。
    return hashlib.sha256(raw.encode()).hexdigest()
