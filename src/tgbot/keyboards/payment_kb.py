from typing import Sequence, Set, Callable, Optional, Dict
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tgbot.lexicon import t

# Заглушки цен
ALL_SUBJECTS_PRICE = "999 ₽"
PER_SUBJECT_PRICE = "249 ₽"


def _truncate_title(title: str, limit: int = 40) -> str:
    return title if len(title) <= limit else (title[:limit] + "…")


def _label_subject_with_price(title: str) -> str:
    base = title if len(title) <= 40 else (title[:40] + "…")
    return f"{base} — {PER_SUBJECT_PRICE}"


def _add_pager(builder: InlineKeyboardBuilder, page: int, last_page: int, prev_cb: str, next_cb: str) -> None:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="<-", callback_data=prev_cb))
    if page < last_page:
        nav.append(InlineKeyboardButton(text="->", callback_data=next_cb))
    if nav:
        builder.row(*nav)


def _add_cart_controls(builder: InlineKeyboardBuilder, cart_count: int, *, open_cb: str = "paysec:cart") -> None:
    if cart_count > 0:
        builder.row(InlineKeyboardButton(text=f"🛒 Корзина ({cart_count})", callback_data=open_cb))
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


def kb_pay_root(
        subjects: Sequence[str],
        page: int = 0,
        per_page: int = 8,
        row_width: int = 2,
        *,
        all_btn_text: Optional[str] = None,
        subject_price_map: Optional[Dict[str, str]] = None,
        payable_subjects: Optional[set[str]] = None,
):
    b = InlineKeyboardBuilder()

    # 1) «Все предметы» — только если есть цена > 0
    if all_btn_text:
        b.row(InlineKeyboardButton(text=all_btn_text, callback_data="pay:buy:all"))

    # 2) Предметы с ценами (если есть)
    total = len(subjects)
    if total > 0:
        start = page * per_page
        end = min(start + per_page, total)
        items = subjects[start:end]

        buttons: list[InlineKeyboardButton] = []
        for i, title in enumerate(items, start=start):
            if payable_subjects is not None and title not in payable_subjects:
                continue
            price = (subject_price_map or {}).get(title)
            label = _truncate_title(title) if not price else f"{_truncate_title(title)} — {price}"
            buttons.append(InlineKeyboardButton(text=label, callback_data=f"pay:subject:{i}"))
        _grid_rows(b, buttons, row_width=row_width)

        last_page = (total - 1) // per_page
        _add_pager(b, page, last_page, prev_cb=f"pay:page:{page - 1}", next_cb=f"pay:page:{page + 1}")

    b.row(InlineKeyboardButton(text="📚 Конкретные разделы", callback_data="pay:sections"))
    b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"))
    return b.as_markup()


def kb_payment_link(payment_url: str):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url), width=1)
    b.row(
        InlineKeyboardButton(text="◀️ В оплату", callback_data="paysec:exit"),
        InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"),
        width=2,
    )
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
        b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="paysec:subjects"),
              InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
              width=2)

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
          InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
          width=2)
    return b.as_markup()


def kb_pay_cart(
        items: Sequence[tuple[str, str]],
        page: int = 0,
        per_page: int = 10,
        row_width: int = 2,
        total_text: str | None = None
):
    b = InlineKeyboardBuilder()
    total = len(items)

    if total == 0:
        b.row(InlineKeyboardButton(text="🛒 Корзина пуста", callback_data="paysec:nop"), width=1)
        b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="paysec:subjects"),
              InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
              width=2)
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    page_items = items[start:end]

    buttons: list[InlineKeyboardButton] = []
    for i, (subj, sec) in enumerate(page_items, start=start):
        label = f"❌ {sec}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"paysec:cartremove:{i}:{page}"))
    _grid_rows(b, buttons, row_width=row_width)

    last_page = (total - 1) // per_page
    _add_pager(b, page, last_page, prev_cb=f"paysec:cartpage:{page - 1}", next_cb=f"paysec:cartpage:{page + 1}")

    checkout_label = f"✅ Оплатить ({total})"
    if total_text:
        checkout_label = f"{checkout_label} — {total_text}"

    b.row(InlineKeyboardButton(text=checkout_label, callback_data="paysec:checkout"))
    b.row(InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="paysec:cartclear"))
    b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="paysec:subjects"),
          InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
          width=2)
    return b.as_markup()
