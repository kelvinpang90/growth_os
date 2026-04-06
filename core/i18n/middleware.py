"""
Locale 中间件 — 从 JWT 或 Accept-Language 头自动设置当前请求的语言环境
"""
import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from core.auth.security import decode_access_token
from core.i18n import set_locale


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        locale = None

        # 1. 优先从 JWT payload 读取用户保存的语言偏好
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = decode_access_token(auth[7:])
                locale = payload.get("language")
            except (jwt.InvalidTokenError, Exception):
                pass

        # 2. 回退到 Accept-Language 请求头
        if not locale:
            accept_lang = request.headers.get("Accept-Language", "en")
            locale = accept_lang[:2].lower()

        set_locale(locale)
        return await call_next(request)
