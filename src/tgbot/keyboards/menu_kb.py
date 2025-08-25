from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_menu_root():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="Оплата", callback_data="menu:pay"),
        InlineKeyboardButton(text="Курсы", callback_data="menu:courses"),
        width=2
    )
    return b.as_markup()


