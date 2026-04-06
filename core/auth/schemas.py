from enum import Enum

from pydantic import BaseModel, EmailStr


class Platform(str, Enum):
    tiktok = "tiktok"
    shopee = "shopee"
    amazon = "amazon"


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    platform: Platform


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    platform: str
    created_at: str
