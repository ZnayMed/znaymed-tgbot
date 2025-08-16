from __future__ import annotations
import os
from typing import List

PROMPT_TTL = int(os.getenv("PROMPT_TTL_SECONDS", "172800"))


def _kinds_key(user_id: int) -> str:
    return f"prompts:{user_id}:kinds"


def _kind_key(user_id: int, kind: str) -> str:
    return f"prompts:{user_id}:{kind}"


async def add_prompt(r, user_id: int, chat_id: int, message_id: int, kind: str) -> None:
    kinds_key = _kinds_key(user_id)
    kind_key = _kind_key(user_id, kind)
    await r.sadd(kind_key, f"{chat_id}:{message_id}")
    await r.sadd(kinds_key, kind)
    await r.expire(kind_key, PROMPT_TTL)
    await r.expire(kinds_key, PROMPT_TTL)


async def list_prompts(r, user_id: int, kind: str) -> List[str]:
    members = await r.smembers(_kind_key(user_id, kind))
    out: list[str] = []
    for m in members:
        out.append(m.decode() if isinstance(m, bytes) else m)
    return out


async def clear_prompts(r, user_id: int, kind: str) -> None:
    kinds_key = _kinds_key(user_id)
    kind_key = _kind_key(user_id, kind)
    await r.delete(kind_key)
    await r.srem(kinds_key, kind)
    # Если набор типов опустел — удалим индекс
    if not await r.scard(kinds_key):
        await r.delete(kinds_key)


# Опционально, если нужно «снести всё» осознанно:
async def clear_all_prompts(r, user_id: int) -> None:
    kinds = await r.smembers(_kinds_key(user_id))
    for k in kinds:
        k = k.decode() if isinstance(k, bytes) else k
        await r.delete(_kind_key(user_id, k))
    await r.delete(_kinds_key(user_id))
