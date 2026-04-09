"""
Global configuration — reads from environment variables, supports .env file
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# 固定路径，无论从哪个目录启动都能正确找到 backend/.env
load_dotenv(Path(__file__).parent.parent / ".env")


def _env(key: str, default: str = "") -> str:
    # 读取环境变量，不存在时返回 default。
    return os.getenv(key, default)


@dataclass
class DBConfig:
    url: str = field(default_factory=lambda: _env(
        "DATABASE_URL",
        "mysql+aiomysql://root:123456@localhost:3306/growth_os?charset=utf8mb4"
    ))
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 3600


@dataclass
class RedisConfig:
    url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0"))
    max_connections: int = 20


@dataclass
class AnthropicConfig:
    # 直接用 os.getenv（返回 None 而不是 ""），避免传空字符串给 SDK 导致认证失败
    api_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"))
    max_tokens: int = 4096


@dataclass
class TikTokConfig:
    app_key: str = field(default_factory=lambda: _env("TIKTOK_APP_KEY"))
    app_secret: str = field(default_factory=lambda: _env("TIKTOK_APP_SECRET"))
    access_token: str = field(default_factory=lambda: _env("TIKTOK_ACCESS_TOKEN"))
    shop_id: str = field(default_factory=lambda: _env("TIKTOK_SHOP_ID"))


@dataclass
class ShopeeConfig:
    partner_id: str = field(default_factory=lambda: _env("SHOPEE_PARTNER_ID"))
    partner_key: str = field(default_factory=lambda: _env("SHOPEE_PARTNER_KEY"))
    access_token: str = field(default_factory=lambda: _env("SHOPEE_ACCESS_TOKEN"))
    shop_id: str = field(default_factory=lambda: _env("SHOPEE_SHOP_ID"))


@dataclass
class LazadaConfig:
    app_key: str = field(default_factory=lambda: _env("LAZADA_APP_KEY"))
    app_secret: str = field(default_factory=lambda: _env("LAZADA_APP_SECRET"))
    access_token: str = field(default_factory=lambda: _env("LAZADA_ACCESS_TOKEN"))


@dataclass
class ShopifyConfig:
    store: str = field(default_factory=lambda: _env("SHOPIFY_STORE"))
    token: str = field(default_factory=lambda: _env("SHOPIFY_TOKEN"))


@dataclass
class AmazonConfig:
    marketplace_id: str = field(default_factory=lambda: _env("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER"))
    seller_id: str = field(default_factory=lambda: _env("AMAZON_SELLER_ID"))
    access_key: str = field(default_factory=lambda: _env("AMAZON_ACCESS_KEY"))
    secret_key: str = field(default_factory=lambda: _env("AMAZON_SECRET_KEY"))


@dataclass
class EmailConfig:
    smtp_host: str = field(default_factory=lambda: _env("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = 587
    username: str = field(default_factory=lambda: _env("SMTP_USERNAME"))
    password: str = field(default_factory=lambda: _env("SMTP_PASSWORD"))
    from_email: str = field(default_factory=lambda: _env("FROM_EMAIL"))


@dataclass
class WhatsAppConfig:
    api_url: str = field(default_factory=lambda: _env("WHATSAPP_API_URL"))
    token: str = field(default_factory=lambda: _env("WHATSAPP_TOKEN"))
    phone_id: str = field(default_factory=lambda: _env("WHATSAPP_PHONE_ID"))


@dataclass
class AuthConfig:
    jwt_secret: str = field(default_factory=lambda: _env("JWT_SECRET", "change-me-in-production"))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(_env("JWT_ACCESS_EXPIRE_MINUTES", "30"))
    )
    refresh_token_expire_days: int = field(
        default_factory=lambda: int(_env("JWT_REFRESH_EXPIRE_DAYS", "30"))
    )


@dataclass
class Settings:
    db: DBConfig = field(default_factory=DBConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    tiktok: TikTokConfig = field(default_factory=TikTokConfig)
    shopee: ShopeeConfig = field(default_factory=ShopeeConfig)
    lazada: LazadaConfig = field(default_factory=LazadaConfig)
    shopify: ShopifyConfig = field(default_factory=ShopifyConfig)
    amazon: AmazonConfig = field(default_factory=AmazonConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    mock_mode: bool = field(default_factory=lambda: _env("MOCK_MODE", "true").lower() == "true")
    debug: bool = field(default_factory=lambda: _env("DEBUG", "false").lower() == "true")


# 全局单例
settings = Settings()
