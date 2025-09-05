from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging

log = logging.getLogger(__name__)


class AutoAnswerMiddleware(BaseMiddleware):
    def __init__(self, text: str | None = None, cache_time: int | None = None, show_alert: bool | None = None):
        self.text = text
        self.cache_time = cache_time
        self.show_alert = show_alert

    async def __call__(self, handler, event, data):
        if isinstance(event, CallbackQuery):
            try:
                await event.answer(text=self.text, cache_time=self.cache_time, show_alert=self.show_alert)
            except TelegramBadRequest as e:
                msg = (getattr(e, "message", "") or str(e)).lower()
                # протухший query игнорируем, остальное пробрасываем
                if "query is too old" not in msg:
                    raise
        return await handler(event, data)
