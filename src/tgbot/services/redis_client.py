import os
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import ConnectionError

_redis: Optional[Redis] = None
_available: Optional[bool] = None  # кэш health-check'а ping()


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # decode_responses=True => все ключи/значения/члены множеств — СТРОКИ
        _redis = Redis.from_url(url, encoding="utf-8", decode_responses=True)
    return _redis


async def is_redis_available() -> bool:
    global _available
    if _available is not None:
        return _available
    r = get_redis()
    try:
        await r.ping()
        _available = True
    except ConnectionError:
        _available = False
    return _available
