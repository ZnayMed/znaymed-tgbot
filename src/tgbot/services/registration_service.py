import contextlib
import httpx
from aiogram import Bot

from tgbot.lexicon import t
from tgbot.services.redis_client import get_redis, is_redis_available
from tgbot.services.reg_prompts import list_prompts, clear_prompts
from tgbot.services.user_cache import (
    is_registered_cached,
    cache_registered,
    is_negative_cached,
    cache_negative,
    clear_negative,
)


async def mute_old_prompts(user_id: int, bot: Bot) -> None:
    # Если Redis недоступен — молча пропускаем
    if not await is_redis_available():
        return
    r = get_redis()
    members = await list_prompts(r, user_id)
    for m in members:
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
    await clear_prompts(r, user_id)


# tgbot/services/registration_service.py

async def ensure_not_registered(user_id: int, bot: Bot, api_client) -> bool:

    r = get_redis()
    redis_up = await is_redis_available()

    # 1) Позитивный кэш — сразу стоп
    if redis_up and await is_registered_cached(r, user_id):
        await mute_old_prompts(user_id, bot)
        await bot.send_message(user_id, t("already_registered"))
        return False

    # 2) Негативный кэш — НО с обязательной ревалидацией по API
    if redis_up and await is_negative_cached(r, user_id):
        try:
            exists = await api_client.user_exists(user_id)
        except httpx.HTTPError:
            await bot.send_message(user_id, t("api_error"))
            return False

        if exists:
            # Обновляем кэш (фиксируем факт регистрации) и показываем сообщение
            await cache_registered(r, user_id)
            await clear_negative(r, user_id)
            await mute_old_prompts(user_id, bot)
            await bot.send_message(user_id, t("already_registered"))
            return False
        # всё ещё не зарегистрирован — разрешаем идти дальше
        return True

    # 3) Кэша нет — спрашиваем API и обновляем кэш
    try:
        exists = await api_client.user_exists(user_id)
    except httpx.HTTPError:
        await bot.send_message(user_id, t("api_error"))
        return False

    if exists:
        if redis_up:
            await cache_registered(r, user_id)
            await clear_negative(r, user_id)
        await mute_old_prompts(user_id, bot)
        await bot.send_message(user_id, t("already_registered"))
        return False

    # Не зарегистрирован — поставим негативный флажок с коротким TTL (если Redis доступен)
    if redis_up:
        await cache_negative(r, user_id)
    return True
