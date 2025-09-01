# tgbot/utils/prompt_cleaner.py
import contextlib
import logging
from aiogram import Bot
from redis.exceptions import ReadOnlyError

from tgbot.services.redis_client import get_redis, is_redis_available
from tgbot.services.reg_prompts import list_prompts, clear_prompts, add_prompt

log = logging.getLogger(__name__)


async def clean_user_prompts(user_id: int, bot: Bot, kind: str) -> None:
    if not await is_redis_available():
        return
    r = get_redis()
    for m in await list_prompts(r, user_id, kind):
        try:
            chat_id_str, msg_id_str = m.split(":")
            chat_id = int(chat_id_str)
            msg_id = int(msg_id_str)
        except Exception:
            continue
        with contextlib.suppress(Exception):
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
        with contextlib.suppress(Exception):
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    try:
        await clear_prompts(r, user_id, kind)
    except ReadOnlyError:
        log.warning("Skip clear_prompts for user=%s kind=%s: Redis is read-only", user_id, kind)


async def register_prompt(user_id: int, chat_id: int, message_id: int, kind: str) -> None:
    if not await is_redis_available():
        return
    r = get_redis()
    try:
        await add_prompt(r, user_id, chat_id, message_id, kind)
    except ReadOnlyError:
        log.warning("Skip add_prompt (read-only) user=%s chat=%s msg=%s kind=%s",
                    user_id, chat_id, message_id, kind)
