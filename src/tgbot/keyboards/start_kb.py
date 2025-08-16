from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_reg() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📝 Регистрация", callback_data="reg")]]
    )
