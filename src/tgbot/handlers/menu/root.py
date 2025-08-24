import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tgbot.lexicon import t
from tgbot.keyboards.menu_kb import kb_menu_root
from .utils import send_single_menu, edit_or_respawn

router = Router(name="menu.root")
log = logging.getLogger(__name__)


async def render_menu_root(msg, user_id: int):
    return await edit_or_respawn(msg, user_id, t("menu_main"), kb_menu_root())


async def send_main_menu(bot, chat_id: int, user_id: int):
    return await send_single_menu(bot, chat_id, user_id, t("menu_main"), kb_menu_root())


@router.message(Command("menu"))
async def cmd_menu(msg: Message):
    await send_main_menu(msg.bot, msg.chat.id, msg.from_user.id)


@router.callback_query(F.data == "menu:root")
async def cb_menu_root(cb: CallbackQuery):
    await cb.answer()
    await render_menu_root(cb.message, cb.from_user.id)
