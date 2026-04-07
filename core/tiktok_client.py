"""
Shared TikTok API signing utility — used by Phase 1 and Phase 2 crawlers
"""
import hashlib
import hmac
import time

from core.config import settings


class TikTokSigner:
    """Encapsulates TikTok Open API HMAC-SHA256 request signing."""

    def __init__(self):
        # 从全局配置读取 TikTok API 凭据并初始化签名器。
        cfg             = settings.tiktok
        self.app_key    = cfg.app_key
        self.app_secret = cfg.app_secret
        self.token      = cfg.access_token
        self.shop_id    = cfg.shop_id

    def sign(self, path: str, params: dict) -> dict:
        # 为请求参数添加时间戳和 HMAC-SHA256 签名，返回含签名的完整参数字典。
        ts = str(int(time.time()))
        p  = {**params, "app_key": self.app_key, "timestamp": ts,
              "access_token": self.token, "shop_id": self.shop_id}
        s  = "".join(f"{k}{v}" for k, v in sorted(p.items()))
        p["sign"] = hmac.new(
            self.app_secret.encode(),
            f"{self.app_secret}{path}{s}{self.app_secret}".encode(),
            hashlib.sha256,
        ).hexdigest().upper()
        return p
