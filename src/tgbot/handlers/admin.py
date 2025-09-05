import logging
from aiogram import Router, F
from aiogram.types import Message

from tgbot.filters.is_admin import IsAdmin

router = Router(name="admin")
log = logging.getLogger(__name__)


@router.message(IsAdmin(), F.video)
async def reply_video_id(message: Message):
    v = message.video
    await message.reply(
        f"file_id:\n<code>{v.file_id}</code>"
    )
