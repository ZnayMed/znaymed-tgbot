from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from tgbot.services.api_client import APIGatewayClient


class IsAdmin(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery], api: APIGatewayClient) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        try:
            return await api.is_admin(user.id)
        except Exception:
            return False
