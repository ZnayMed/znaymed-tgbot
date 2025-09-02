import contextlib

from aiogram.exceptions import TelegramBadRequest
from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt
from tgbot.utils.click_guard import get_user_lock

MENU_KIND = "menu"


async def send_single_menu(bot, chat_id: int, user_id: int, text: str, reply_markup):
    lock = get_user_lock(user_id)
    async with lock:
        await clean_user_prompts(user_id, bot, kind=MENU_KIND)
        sent = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
        await register_prompt(user_id, sent.chat.id, sent.message_id, kind=MENU_KIND)
        return sent


async def edit_or_respawn(msg, user_id: int, text: str, reply_markup):
    lock = get_user_lock(user_id)
    async with lock:
        try:
            return await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except TelegramBadRequest as e:
            em = (getattr(e, "message", "") or str(e)).lower()

            if "message is not modified" in em:
                return msg

            if (
                    "message to edit not found" in em
                    or "message can't be edited" in em
                    or "chat not found" in em
            ):
                with contextlib.suppress(Exception):
                    await msg.bot.edit_message_reply_markup(
                        chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=None
                    )
                return await send_single_menu(msg.bot, msg.chat.id, user_id, text, reply_markup)

            raise
