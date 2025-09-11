import contextlib

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMediaVideo

from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt
from tgbot.utils.click_guard import get_user_lock

MENU_KIND = "menu"


async def _send_single_menu_unlocked(bot, chat_id: int, user_id: int, text: str, reply_markup):
    await clean_user_prompts(user_id, bot, kind=MENU_KIND)
    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML", protect_content=True)
    await register_prompt(user_id, sent.chat.id, sent.message_id, kind=MENU_KIND)
    return sent


async def send_single_menu(bot, chat_id: int, user_id: int, text: str, reply_markup):
    lock = get_user_lock(user_id)
    async with lock:
        return await _send_single_menu_unlocked(bot, chat_id, user_id, text, reply_markup)


async def edit_or_respawn(msg, user_id: int, text: str, reply_markup):
    lock = get_user_lock(user_id)
    async with lock:
        if getattr(msg, "text", None) is None:
            with contextlib.suppress(Exception):
                await msg.bot.edit_message_reply_markup(
                    chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=None
                )
            return await _send_single_menu_unlocked(msg.bot, msg.chat.id, user_id, text, reply_markup)

        try:
            return await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except TelegramBadRequest as e:
            em = (getattr(e, "message", "") or str(e)).lower()

            if "message is not modified" in em:
                return msg

            if (
                    "there is no text in the message to edit" in em
                    or "message to edit not found" in em
                    or "message can't be edited" in em
                    or "chat not found" in em
            ):
                with contextlib.suppress(Exception):
                    await msg.bot.edit_message_reply_markup(
                        chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=None
                    )
                return await _send_single_menu_unlocked(msg.bot, msg.chat.id, user_id, text, reply_markup)

            raise


async def send_single_menu_media(bot, chat_id: int, user_id: int, *,
                                 video_file_id: str,
                                 caption_html: str,
                                 reply_markup,
                                 protect_content: bool = True):
    lock = get_user_lock(user_id)
    async with lock:
        await clean_user_prompts(user_id, bot, kind=MENU_KIND)
        sent = await bot.send_video(
            chat_id=chat_id,
            video=video_file_id,
            caption=caption_html,
            reply_markup=reply_markup,
            parse_mode="HTML",
            protect_content=protect_content,
            disable_notification=True
        )
        await register_prompt(user_id, sent.chat.id, sent.message_id, kind=MENU_KIND)
        return sent


async def edit_or_respawn_media(msg, user_id: int, *,
                                media: InputMediaVideo,
                                reply_markup,
                                protect_content: bool = True):
    lock = get_user_lock(user_id)
    async with lock:
        try:
            return await msg.bot.edit_message_media(
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                media=media,
                reply_markup=reply_markup,
            )
        except TelegramBadRequest as e:
            em = (getattr(e, "message", "") or str(e)).lower()

            if "message is not modified" in em:
                return msg

            if (
                    "message to edit not found" in em
                    or "message can't be edited" in em
                    or "can't change media of a message" in em
                    or "chat not found" in em
                    or "message content is not modified" in em
            ):
                with contextlib.suppress(Exception):
                    await msg.bot.edit_message_reply_markup(
                        chat_id=msg.chat.id, message_id=msg.message_id, reply_markup=None
                    )

                return await send_single_menu_media(
                    msg.bot, msg.chat.id, user_id,
                    video_file_id=media.media,
                    caption_html=media.caption or "",
                    reply_markup=reply_markup,
                    protect_content=protect_content
                )

            raise
