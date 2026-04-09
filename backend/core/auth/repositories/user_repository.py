"""
User Repository — all SQL for the users and refresh_tokens tables.
"""
from datetime import datetime

from core.database import execute, fetchone


async def get_user_by_email_or_username(email: str, username: str) -> dict | None:
    return await fetchone(
        "SELECT id FROM users WHERE email = :email OR username = :username",
        {"email": email, "username": username},
    )


async def get_user_by_email(email: str) -> dict | None:
    return await fetchone(
        "SELECT id, username, password_hash, language FROM users WHERE email = :email AND is_active = 1",
        {"email": email},
    )


async def get_user_simple(email: str) -> dict | None:
    """Return id, username, language after insert."""
    return await fetchone(
        "SELECT id, username, language FROM users WHERE email = :email",
        {"email": email},
    )


async def create_user(
    username: str,
    email: str,
    password_hash: str,
    platform: str,
    language: str,
    currency: str,
) -> None:
    await execute(
        """
        INSERT INTO users (username, email, password_hash, platform, language, currency)
        VALUES (:username, :email, :password_hash, :platform, :language, :currency)
        """,
        {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "platform": platform,
            "language": language,
            "currency": currency,
        },
    )


async def get_user_full(user_id: int) -> dict | None:
    return await fetchone(
        "SELECT id, username, email, platform, language, currency, created_at "
        "FROM users WHERE id = :id AND is_active = 1",
        {"id": user_id},
    )


async def get_password_hash(user_id: int) -> dict | None:
    return await fetchone(
        "SELECT password_hash FROM users WHERE id = :id",
        {"id": user_id},
    )


async def update_user(user_id: int, updates: dict) -> None:
    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = user_id
    await execute(f"UPDATE users SET {set_clause} WHERE id = :id", updates)


async def get_refresh_token(token_hash: str) -> dict | None:
    return await fetchone(
        """
        SELECT rt.user_id, rt.expires_at, u.username, u.language
        FROM refresh_tokens rt
        JOIN users u ON u.id = rt.user_id
        WHERE rt.token_hash = :token_hash AND u.is_active = 1
        """,
        {"token_hash": token_hash},
    )


async def save_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> None:
    await execute(
        """
        INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
        VALUES (:user_id, :token_hash, :expires_at)
        """,
        {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
    )


async def delete_refresh_token(token_hash: str) -> None:
    await execute(
        "DELETE FROM refresh_tokens WHERE token_hash = :h",
        {"h": token_hash},
    )
