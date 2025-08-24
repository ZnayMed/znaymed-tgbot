from typing import Sequence, Set, Callable
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Заглушки цен
ALL_SUBJECTS_PRICE = "999 ₽"
PER_SUBJECT_PRICE = "249 ₽"


def _label_subject_with_price(title: str) -> str:
    base = title if len(title) <= 40 else (title[:40] + "…")
    return f"{base} — {PER_SUBJECT_PRICE}"


def _add_pager(builder: InlineKeyboardBuilder, page: int, last_page: int, prev_cb: str, next_cb: str) -> None:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⟨ Назад", callback_data=prev_cb))
    if page < last_page:
        nav.append(InlineKeyboardButton(text="Вперёд ⟩", callback_data=next_cb))
    if nav:
        builder.row(*nav)


def _add_cart_controls(builder: InlineKeyboardBuilder, cart_count: int) -> None:
    if cart_count > 0:
        builder.row(InlineKeyboardButton(text=f"🛒 Корзина ({cart_count})", callback_data="paysec:checkout"))
    else:
        builder.row(InlineKeyboardButton(text="🛒 Корзина пуста", callback_data="paysec:nop"))


def _grid_rows(builder: InlineKeyboardBuilder, buttons: list[InlineKeyboardButton], row_width: int) -> None:
    row: list[InlineKeyboardButton] = []
    for btn in buttons:
        row.append(btn)
        if len(row) == row_width:
            builder.row(*row)
            row = []
    if row:
        builder.row(*row)


def kb_pay_root(subjects: Sequence[str], page: int = 0, per_page: int = 8, row_width: int = 2):
    b = InlineKeyboardBuilder()

    # 1) Все предметы
    b.row(InlineKeyboardButton(text=f"Все предметы — {ALL_SUBJECTS_PRICE}", callback_data="pay:buy:all"))

    # 2) Предметы с ценой
    total = len(subjects)
    if total > 0:
        start = page * per_page
        end = min(start + per_page, total)
        items = subjects[start:end]

        buttons = [
            InlineKeyboardButton(text=_label_subject_with_price(title), callback_data=f"pay:subject:{i}")
            for i, title in enumerate(items, start=start)
        ]
        _grid_rows(b, buttons, row_width=row_width)

        last_page = (total - 1) // per_page
        _add_pager(b, page, last_page, prev_cb=f"pay:page:{page - 1}", next_cb=f"pay:page:{page + 1}")

    # 3) Конкретные разделы + назад
    b.row(InlineKeyboardButton(text="📚 Конкретные разделы", callback_data="pay:sections"))
    b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"))
    return b.as_markup()


def kb_pay_sections_subjects(
        subjects: Sequence[str],
        page: int = 0,
        per_page: int = 9,
        row_width: int = 2,
        cart_count: int = 0,
):
    b = InlineKeyboardBuilder()
    total = len(subjects)

    if total == 0:
        _add_cart_controls(b, cart_count)
        b.row(InlineKeyboardButton(text="◀️ В оплату", callback_data="paysec:exit"),
              InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
              width=2)
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = subjects[start:end]

    buttons = [
        InlineKeyboardButton(text=title, callback_data=f"paysec:open:{i}")
        for i, title in enumerate(items, start=start)
    ]
    _grid_rows(b, buttons, row_width=row_width)

    last_page = (total - 1) // per_page
    _add_pager(b, page, last_page, prev_cb=f"paysec:page:{page - 1}", next_cb=f"paysec:page:{page + 1}")

    _add_cart_controls(b, cart_count)
    b.row(InlineKeyboardButton(text="◀️ В оплату", callback_data="paysec:exit"),
          InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
          width=2)

    return b.as_markup()


def kb_pay_sections_list(
        subject: str,
        sections_locked: Sequence[dict],
        selected_keys: Set[str],
        encode_fn: Callable[[str, str], str],
        subj_idx: int,
        page: int = 0,
        per_page: int = 10,
        row_width: int = 2,
        cart_count: int = 0,
):
    b = InlineKeyboardBuilder()
    total = len(sections_locked)

    if total == 0:
        b.row(InlineKeyboardButton(text="Все разделы уже доступны 🎉", callback_data="paysec:nop"))
        b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="paysec:subjects"))
        b.row(InlineKeyboardButton(text="◀️ В оплату", callback_data="paysec:exit"))
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = sections_locked[start:end]

    buttons: list[InlineKeyboardButton] = []
    for i, s in enumerate(items, start=start):
        title = s.get("title", "")
        selected = encode_fn(subject, title) in selected_keys
        label = f"{'✅' if selected else '➕'} {title}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"paysec:toggle:{subj_idx}:{i}:{page}"))
    _grid_rows(b, buttons, row_width=row_width)

    last_page = (total - 1) // per_page
    _add_pager(b, page, last_page, prev_cb=f"paysec:sectpage:{subj_idx}:{page - 1}",
               next_cb=f"paysec:sectpage:{subj_idx}:{page + 1}")

    _add_cart_controls(b, cart_count)
    b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="paysec:subjects"),
          InlineKeyboardButton(text="◀️ В оплату", callback_data="paysec:exit"),
          width=2)
    b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"))
    return b.as_markup()
