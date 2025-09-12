from aiogram import BaseMiddleware
from aiogram.types import Message
import httpx

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.services.redis_client import get_redis, is_redis_available
from tgbot.services.user_cache import is_registered_cached, cache_registered


class RegistrationGuardMiddleware(BaseMiddleware):
    def __init__(self, api: APIGatewayClient, allowed: set[str] | None = None):
        self.api = api
        self.allowed = allowed or {"/start", "/info", "/help"}

    async def __call__(self, handler, event: Message, data):
        txt = event.text or ""
        if not txt.startswith("/"):
            return await handler(event, data)

        cmd = txt.split()[0]
        if cmd in self.allowed:
            return await handler(event, data)

        uid = event.from_user.id
        r = get_redis()
        redis_up = await is_redis_available()

        # 1) Redis
        if redis_up and await is_registered_cached(r, uid):
            return await handler(event, data)

        # 2) API
        try:
            exists = await self.api.user_exists(uid)
        except httpx.HTTPError:
            # сеть недоступна — не ломаем UX, пропускаем
            return await handler(event, data)

        if exists:
            if redis_up:
                await cache_registered(r, uid)
            return await handler(event, data)

        # 3) Не зарегистрирован — блокируем
        await event.answer(t("need_register"))
        return
