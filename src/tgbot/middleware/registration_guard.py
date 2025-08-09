from aiogram import BaseMiddleware
from aiogram.types import Message
import httpx

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient


class RegistrationGuardMiddleware(BaseMiddleware):
    """Блокирует все команды, кроме /start, если юзер не зарегистрирован."""

    def __init__(self, api: APIGatewayClient):
        self.api = api
        self._allowed = {"/start", "/info"}

    async def __call__(self, handler, event: Message, data):
        if event.text and event.text.startswith("/"):
            command = event.text.split()[0]
            if command not in self._allowed:
                try:
                    if await self.api.user_exists(event.from_user.id):
                        return
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        await event.answer(t("need_register"))
                        return
                except httpx.HTTPError:
                    pass  # сеть недоступна – пропускаем
        return await handler(event, data)
