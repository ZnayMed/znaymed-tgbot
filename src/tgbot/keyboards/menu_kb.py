# tgbot/keyboards/menu_kb.py
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


def kb_subjects(subjects: list[str], page: int = 0, per_page: int = 9, row_width: int = 3):
    b = InlineKeyboardBuilder()
    total = len(subjects)
    if total == 0:
        # только назад
        b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu:root"))
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = subjects[start:end]

    # кнопки предметов по индексам
    row = []
    for i, title in enumerate(items, start=start):
        row.append(InlineKeyboardButton(text=title, callback_data=f"courses:open:{i}"))
        if len(row) == row_width:
            b.row(*row)
            row = []
    if row:
        b.row(*row)

    # пагинация
    last_page = (total - 1) // per_page
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⟨ Назад", callback_data=f"courses:page:{page - 1}"))
    if page < last_page:
        nav.append(InlineKeyboardButton(text="Вперёд ⟩", callback_data=f"courses:page:{page + 1}"))
    if nav:
        b.row(*nav)

    # назад в корень меню
    b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"))
    return b.as_markup()
