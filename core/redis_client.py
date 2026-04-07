"""Redis cache client"""
import json
from typing import Any

import redis.asyncio as aioredis

from core.config import settings
from core.logger import logger

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    # 获取或初始化 Redis 连接池单例。
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis.url, decode_responses=True, max_connections=settings.redis.max_connections)
        logger.info("Redis 连接池初始化完成")
    return _redis


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    # 将值序列化为 JSON 后写入 Redis，设置 TTL 过期时间（默认 1 小时）。
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))


async def cache_get(key: str) -> Any | None:
    # 从 Redis 读取并反序列化缓存值，不存在时返回 None。
    r = await get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def cache_delete(key: str) -> None:
    # 删除指定 Redis 缓存键。
    r = await get_redis()
    await r.delete(key)
