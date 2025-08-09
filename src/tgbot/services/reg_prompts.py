from typing import Iterable
from redis.asyncio import Redis

TTL_SECONDS = 24 * 60 * 60  # 1 сутки


def _key(user_id: int) -> str:
    return f"reg:prompts:{user_id}"


async def add_prompt(redis: Redis, user_id: int, chat_id: int, message_id: int) -> None:
    member = f"{chat_id}:{message_id}"
    await redis.sadd(_key(user_id), member)
    await redis.expire(_key(user_id), TTL_SECONDS)


async def list_prompts(redis: Redis, user_id: int) -> list[str]:
    members = await redis.smembers(_key(user_id))
    return list(members or [])


async def clear_prompts(redis: Redis, user_id: int) -> None:
    await redis.delete(_key(user_id))
