from typing import Optional
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

REG_KEY_PREFIX = "reg:user:"
REG_TTL = 86400  # 24 часа в секундах


def _key(user_id: int | str) -> str:
    return f"{REG_KEY_PREFIX}{user_id}"


async def is_registered_cached(r: Redis, user_id: int | str) -> bool:
    try:
        return bool(await r.exists(_key(user_id)))
    except ConnectionError:
        return False


async def cache_registered(r: Redis, user_id: int | str) -> None:
    try:
        await r.set(_key(user_id), 1, ex=REG_TTL)  # ex — TTL
    except ConnectionError:
        pass
