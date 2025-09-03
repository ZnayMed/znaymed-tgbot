from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ===== helpers =====

def _add_pager(builder: InlineKeyboardBuilder, page: int, last_page: int, prev_cb: str, next_cb: str) -> None:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⟨ Назад", callback_data=prev_cb))
    if page < last_page:
        nav.append(InlineKeyboardButton(text="Вперёд ⟩", callback_data=next_cb))
    if nav:
        builder.row(*nav, width=len(nav))


def _grid_rows(builder: InlineKeyboardBuilder, buttons: list[InlineKeyboardButton], row_width: int) -> None:
    row: list[InlineKeyboardButton] = []
    for btn in buttons:
        row.append(btn)
        if len(row) == row_width:
            builder.row(*row, width=row_width)
            row = []
    if row:
        builder.row(*row, width=len(row))


def _shorten(text: str, max_len: int = 40) -> str:
    return (text[:max_len] + "…") if len(text) > max_len else text


# ===== keyboards =====

def kb_subjects(subjects: list[str], page: int = 0, per_page: int = 9, row_width: int = 3):
    b = InlineKeyboardBuilder()
    total = len(subjects)
    if total == 0:
        b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"), width=1)
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = subjects[start:end]

    buttons = [
        InlineKeyboardButton(text=_shorten(title), callback_data=f"courses:open:{i}")
        for i, title in enumerate(items, start=start)
    ]
    _grid_rows(b, buttons, row_width=row_width)

    last_page = (total - 1) // per_page
    _add_pager(b, page, last_page, prev_cb=f"courses:page:{page - 1}", next_cb=f"courses:page:{page + 1}")

    b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"), width=1)
    return b.as_markup()


def kb_sections(sections: list[dict], subj_idx: int, page: int = 0, per_page: int = 10, row_width: int = 2):
    b = InlineKeyboardBuilder()
    total = len(sections)
    if total == 0:
        b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="menu:courses"), width=1)
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = sections[start:end]

    buttons: list[InlineKeyboardButton] = []
    for i, s in enumerate(items, start=start):
        title = s.get("title", "") or ""
        acc = bool(s.get("accessible"))
        text = _shorten(title) if acc else f"🔒 {_shorten(title)}"
        cb = f"sect:open:{subj_idx}:{i}" if acc else f"menu:pay"
        buttons.append(InlineKeyboardButton(text=text, callback_data=cb))
    _grid_rows(b, buttons, row_width=row_width)

    last_page = (total - 1) // per_page
    _add_pager(
        b, page, last_page,
        prev_cb=f"sect:page:{subj_idx}:{page - 1}",
        next_cb=f"sect:page:{subj_idx}:{page + 1}"
    )

    b.row(
        InlineKeyboardButton(text="◀️ К предметам", callback_data="menu:courses"),
        InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"),
        width=2
    )
    return b.as_markup()


def kb_topics(topics: list[dict], subj_idx: int, sect_idx: int, page: int = 0, per_page: int = 8, row_width: int = 1):
    b = InlineKeyboardBuilder()
    total = len(topics)
    if total == 0:
        b.row(InlineKeyboardButton(text="◀️ К разделам", callback_data=f"sect:back:{subj_idx}"), width=1)
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = topics[start:end]

    buttons = [
        InlineKeyboardButton(
            text=_shorten(t.get("title", "") or "", 40),
            callback_data=f"topic:view:{subj_idx}:{sect_idx}:{i}:{page}"
        )
        for i, t in enumerate(items, start=start)
    ]
    _grid_rows(b, buttons, row_width=row_width)

    last_page = (total - 1) // per_page
    _add_pager(
        b, page, last_page,
        prev_cb=f"topics:page:{subj_idx}:{sect_idx}:{page - 1}",
        next_cb=f"topics:page:{subj_idx}:{sect_idx}:{page + 1}"
    )

    b.row(
        InlineKeyboardButton(text="◀️ К разделам", callback_data=f"sect:back:{subj_idx}"),
        InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"),
        width=2
    )
    return b.as_markup()


def kb_topic_detail(has_video: bool, mindmap_url: str | None, subj_idx: int, sect_idx: int, topic_idx: int,
                    back_page: int):
    b = InlineKeyboardBuilder()
    row = []
    if has_video:
        row.append(InlineKeyboardButton(
            text="▶️ Видео",
            callback_data=f"topic:video:{subj_idx}:{sect_idx}:{topic_idx}:{back_page}"
        ))
    if mindmap_url:
        row.append(InlineKeyboardButton(text="🧠 Майнкарта", url=mindmap_url))
    if row:
        b.row(*row, width=len(row))

    b.row(
        InlineKeyboardButton(text="◀️ К темам", callback_data=f"topics:page:{subj_idx}:{sect_idx}:{back_page}"),
        InlineKeyboardButton(text="◀️ В меню", callback_data="paysec:exit_menu"),
        width=2
    )

    return b.as_markup()
