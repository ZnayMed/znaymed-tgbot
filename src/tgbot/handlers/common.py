from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.lexicon import t

router = Router(name="info")


@router.message(Command("info"))
async def cmd_info(msg: Message):
    await msg.answer(t("info_text"), disable_web_page_preview=True)


@router.message(Command("help"))
async def cmd_info(msg: Message):
    await msg.answer(t("help_text"), disable_web_page_preview=True)
