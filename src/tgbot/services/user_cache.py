from typing import Optional
from redis.asyncio import Redis
from redis.exceptions import ConnectionError

REG_SET = "reg:users"  # множество с user_id зарегистрированных (храним как строки)
NEG_PREFIX = "reg:nx"  # ключи негативного кэша
NEG_TTL = 30  # сек — держим "не зарегистрирован" недолго


def _uid(user_id: int | str) -> str:
    # Всё приводим к строкам — т.к. decode_responses=True
    return str(user_id)


async def is_registered_cached(r: Redis, user_id: int | str) -> bool:
    try:
        return bool(await r.sismember(REG_SET, _uid(user_id)))
    except ConnectionError:
        return False


async def cache_registered(r: Redis, user_id: int | str) -> None:
    try:
        await r.sadd(REG_SET, _uid(user_id))
    except ConnectionError:
        pass


async def is_negative_cached(r: Redis, user_id: int | str) -> bool:
    try:
        return (await r.exists(f"{NEG_PREFIX}:{_uid(user_id)}")) == 1
    except ConnectionError:
        return False


async def cache_negative(r: Redis, user_id: int | str) -> None:
    try:
        await r.set(f"{NEG_PREFIX}:{_uid(user_id)}", "1", ex=NEG_TTL, nx=True)
    except ConnectionError:
        pass


async def clear_negative(r: Redis, user_id: int | str) -> None:
    try:
        await r.delete(f"{NEG_PREFIX}:{_uid(user_id)}")
    except ConnectionError:
        pass
