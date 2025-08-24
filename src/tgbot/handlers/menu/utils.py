import contextlib
from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt

MENU_KIND = "menu"


async def send_single_menu(bot, chat_id: int, user_id: int, text: str, reply_markup):
    await clean_user_prompts(user_id, bot, kind=MENU_KIND)
    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    await register_prompt(user_id, sent.chat.id, sent.message_id, kind=MENU_KIND)
    return sent


async def edit_or_respawn(msg, user_id: int, text: str, reply_markup):
    try:
        return await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        with contextlib.suppress(Exception):
            await msg.delete()
        return await send_single_menu(msg.bot, msg.chat.id, user_id, text, reply_markup)
