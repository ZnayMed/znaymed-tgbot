from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from tgbot.services.api_client import APIGatewayClient


class APIClientMiddleware(BaseMiddleware):
    def __init__(self, client: APIGatewayClient):
        self.client = client

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any],
    ):
        data["api_client"] = self.client
        return await handler(event, data)
