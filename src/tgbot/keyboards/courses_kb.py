from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_subjects(subjects: list[str], page: int = 0, per_page: int = 9, row_width: int = 3):
    b = InlineKeyboardBuilder()
    total = len(subjects)
    if total == 0:
        b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"))
        return b.as_markup()
    start = page * per_page
    end = min(start + per_page, total)
    items = subjects[start:end]

    row = []
    for i, title in enumerate(items, start=start):
        row.append(InlineKeyboardButton(text=title, callback_data=f"courses:open:{i}"))
        if len(row) == row_width:
            b.row(*row)
            row = []
    if row:
        b.row(*row)

    last_page = (total - 1) // per_page
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⟨ Назад", callback_data=f"courses:page:{page - 1}"))
    if page < last_page:
        nav.append(InlineKeyboardButton(text="Вперёд ⟩", callback_data=f"courses:page:{page + 1}"))
    if nav:
        b.row(*nav)

    b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"))
    return b.as_markup()


def kb_sections(sections: list[dict], subj_idx: int, page: int = 0, per_page: int = 10, row_width: int = 2):
    b = InlineKeyboardBuilder()
    total = len(sections)
    if total == 0:
        b.row(InlineKeyboardButton(text="◀️ К предметам", callback_data="menu:courses"))
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = sections[start:end]

    row = []
    for i, s in enumerate(items, start=start):
        title = s.get("title", "")
        acc = bool(s.get("accessible"))
        text = title if acc else f"🔒 {title}"
        cb = f"sect:open:{subj_idx}:{i}" if acc else f"sect:locked:{subj_idx}:{i}"
        row.append(InlineKeyboardButton(text=text, callback_data=cb))
        if len(row) == row_width:
            b.row(*row)
            row = []
    if row: b.row(*row)

    last_page = (total - 1) // per_page
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⟨ Назад", callback_data=f"sect:page:{subj_idx}:{page - 1}"))
    if page < last_page:
        nav.append(
            InlineKeyboardButton(text="Вперёд ⟩", callback_data=f"sect:page:{subj_idx}:{page + 1}"))
    if nav:
        b.row(*nav)

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
        b.row(InlineKeyboardButton(text="◀️ К разделам", callback_data=f"sect:back:{subj_idx}"))
        return b.as_markup()

    start = page * per_page
    end = min(start + per_page, total)
    items = topics[start:end]

    row = []
    for i, t in enumerate(items, start=start):
        title = t.get("title", "")
        # разумная обрезка подписи кнопки
        label = (title[:40] + "…") if len(title) > 41 else title
        row.append(InlineKeyboardButton(text=label, callback_data=f"topic:view:{subj_idx}:{sect_idx}:{i}:{page}"))
        if len(row) == row_width:
            b.row(*row)
            row = []
    if row:
        b.row(*row)

    last_page = (total - 1) // per_page
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⟨ Назад", callback_data=f"topics:page:{subj_idx}:{sect_idx}:{page - 1}"))
    if page < last_page:
        nav.append(
            InlineKeyboardButton(text="Вперёд ⟩", callback_data=f"topics:page:{subj_idx}:{sect_idx}:{page + 1}"))
    if nav:
        b.row(*nav)

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
        row.append(InlineKeyboardButton(text="▶️ Видео",
                                        callback_data=f"topic:video:{subj_idx}:{sect_idx}:{topic_idx}:{back_page}"))
    if mindmap_url:
        row.append(InlineKeyboardButton(text="🧠 Майнкарта", url=mindmap_url))
    if row:
        b.row(*row)
    b.row(InlineKeyboardButton(text="◀️ К темам", callback_data=f"topics:page:{subj_idx}:{sect_idx}:{back_page}"),
          InlineKeyboardButton(text="◀️ К разделам", callback_data=f"sect:back:{subj_idx}"),
          width=2)
    return b.as_markup()
