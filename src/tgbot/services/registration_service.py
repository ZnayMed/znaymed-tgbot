import httpx
from aiogram import Bot

from tgbot.lexicon import t
from tgbot.services.redis_client import get_redis, is_redis_available
from tgbot.services.user_cache import is_registered_cached, cache_registered
from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt


async def ensure_not_registered(user_id: int, bot: Bot, api_client) -> bool:
    r = get_redis()
    redis_up = await is_redis_available()

    # 1) Быстрая проверка по позитивному кэшу в Redis
    if redis_up and await is_registered_cached(r, user_id):
        # чистим только экраны регистрации; меню покажет вызывающий код
        await clean_user_prompts(user_id, bot, kind="reg")
        await bot.send_message(user_id, t("already_registered"))
        return False

    # 2) Проверка через API
    try:
        exists = await api_client.user_exists(user_id)
    except httpx.HTTPError:
        await bot.send_message(user_id, t("api_error"))
        return False

    if exists:
        if redis_up:
            await cache_registered(r, user_id)
        await clean_user_prompts(user_id, bot, kind="reg")
        await bot.send_message(user_id, t("already_registered"))
        return False

    # 3) Не зарегистрирован — продолжаем
    return True
