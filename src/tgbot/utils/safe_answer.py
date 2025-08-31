from aiogram.exceptions import TelegramBadRequest
import logging

log = logging.getLogger(__name__)


async def safe_answer(cb, *args, **kwargs):
    try:
        await cb.answer(*args, **kwargs)
    except TelegramBadRequest as e:
        msg = (getattr(e, "message", "") or str(e)).lower()
        if "query is too old" in msg or "query is too old and response timeout" in msg:
            # протухший колбэк — игнорируем, чтобы не падало всё событие
            log.debug("Ignored stale callback query id=%s", getattr(cb, "id", "?"))
            return
        raise  # остальные ошибки важны
