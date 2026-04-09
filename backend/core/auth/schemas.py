from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class Platform(str, Enum):
    tiktok = "tiktok"
    shopee = "shopee"
    amazon = "amazon"


class Language(str, Enum):
    zh = "zh"
    en = "en"


class Currency(str, Enum):
    CNY = "CNY"
    MYR = "MYR"


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    platform: Platform
    language: Language = Language.en
    currency: Currency = Currency.MYR


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
    language: str
    currency: str
    created_at: str


class UpdateUserRequest(BaseModel):
    current_password: Optional[str] = None
    new_password:     Optional[str] = None
    language:         Optional[Language] = None
    currency:         Optional[Currency] = None
