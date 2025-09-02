import contextlib

from aiogram.exceptions import TelegramBadRequest

from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt

MENU_KIND = "menu"


async def send_single_menu(bot, chat_id: int, user_id: int, text: str, reply_markup):
    await clean_user_prompts(user_id, bot, kind=MENU_KIND)
    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    await register_prompt(user_id, sent.chat.id, sent.message_id, kind=MENU_KIND)
    return sent


async def edit_or_respawn(msg, user_id: int, text: str, reply_markup):
    try:
        # если текст/клавиатура те же самые, телега может бросить "message is not modified"
        return await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        em = (getattr(e, "message", "") or str(e)).lower()

        # 1) Нечего менять — ничего не создаём заново
        if "message is not modified" in em:
            return msg

        # 2) Старое сообщение уже нельзя редактировать — создаём новое
        if (
                "message to edit not found" in em
                or "message can't be edited" in em
                or "message to edit not found" in em
                or "chat not found" in em
        ):
            # На всякий случай уберём клавиатуру у старого, чтобы по ней не кликали
            with contextlib.suppress(Exception):
                await msg.bot.edit_message_reply_markup(chat_id=msg.chat.id, message_id=msg.message_id,
                                                        reply_markup=None)
            return await send_single_menu(msg.bot, msg.chat.id, user_id, text, reply_markup)

        # 3) Любая другая причина — пробрасываем, чтобы не плодить дубли «на всякий случай»
        raise
