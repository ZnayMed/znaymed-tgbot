import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaVideo

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.courses_kb import kb_subjects, kb_sections, kb_topics, kb_topic_links
from tgbot.utils.edit_or_respawn import edit_or_respawn, edit_or_respawn_media

router = Router(name="menu.courses")
log = logging.getLogger(__name__)

PER_PAGE_SUBJ = 9
PER_PAGE_SECT = 10
PER_PAGE_TOPICS = 10


async def render_subjects(msg, user_id: int, api: APIGatewayClient, page: int = 0):
    try:
        subjects = await api.get_subjects()
        subject_titles = api.subject_titles(subjects)
    except Exception:
        return await edit_or_respawn(msg, user_id, t("courses_error"), kb_subjects([], page=0))

    # Текст как раньше (без описаний на экране предметов)
    text = t("courses_title") if subjects else t("courses_empty")

    return await edit_or_respawn(
        msg, user_id, text,
        kb_subjects(subject_titles, page=page, per_page=PER_PAGE_SUBJ)
    )


async def render_sections(msg, user_id: int, api: APIGatewayClient, subj_idx: int, page: int = 0):
    try:
        subjects = await api.get_subjects()
        subject_titles = api.subject_titles(subjects)
        subject = subjects[subj_idx]
        subject_title = (subject.get("title") or "").strip()
        subject_desc = (subject.get("description") or "").strip()
    except Exception:
        try:
            subjects = await api.get_subjects()
            titles = api.subject_titles(subjects)
        except Exception:
            titles = []
        return await edit_or_respawn(msg, user_id, t("sections_error"), kb_subjects(titles, page=0))

    try:
        sections = await api.get_subject_sections(user_id, subject_title)  # с description
    except Exception:
        return await edit_or_respawn(msg, user_id, t("sections_error"), kb_subjects(subject_titles, page=0))

    lines = [f"<b>{subject_title}</b>", ""]
    if subject_desc:
        lines.append(subject_desc)
    lines.append("")
    lines.append(t("sections_hint"))
    text = "\n\n".join(lines)

    return await edit_or_respawn(
        msg, user_id, text,
        kb_sections(sections, subj_idx=subj_idx, page=page, per_page=PER_PAGE_SECT)
    )


async def render_topics(msg, user_id: int, api: APIGatewayClient, subj_idx: int, sect_idx: int, page: int = 0):
    subjects = await api.get_subjects()
    subject_titles = api.subject_titles(subjects)
    subject_title = subject_titles[subj_idx]

    sections = await api.get_subject_sections(user_id, subject_title)
    if not (0 <= sect_idx < len(sections)):
        return await edit_or_respawn(msg, user_id, t("topics_error"),
                                     kb_sections(sections, subj_idx=subj_idx, page=0))

    section = sections[sect_idx]
    section_title = (section.get("title") or "").strip()
    section_desc = (section.get("description") or "").strip()

    try:
        payload = await api.get_section_topics(section_title)
        topics = list(payload.get("topics") or [])
    except Exception:
        return await edit_or_respawn(msg, user_id, t("topics_error"),
                                     kb_sections(sections, subj_idx=subj_idx, page=0))

    lines = [f"<b>{section_title}</b>", ""]
    if section_desc:
        lines.append(section_desc)
    lines.append("")
    lines.append(t("topics_hint"))
    text = "\n".join(lines)

    return await edit_or_respawn(
        msg, user_id, text,
        kb_topics(topics, subj_idx=subj_idx, sect_idx=sect_idx, page=page, per_page=PER_PAGE_TOPICS)
    )


async def render_topic_view(msg, user_id: int, api: APIGatewayClient,
                            subj_idx: int, sect_idx: int, topic_idx: int, back_page: int):
    subjects = await api.get_subjects()
    subject_titles = api.subject_titles(subjects)
    subject_title = subject_titles[subj_idx]

    sections = await api.get_subject_sections(user_id, subject_title)
    if not (0 <= sect_idx < len(sections)):
        return await render_sections(msg, user_id, api, subj_idx=subj_idx, page=0)

    section_title = (sections[sect_idx].get("title") or "").strip()

    data = await api.get_section_topics(section_title)
    topics = list(data.get("topics") or [])
    if not (0 <= topic_idx < len(topics)):
        return await render_topics(msg, user_id, api, subj_idx, sect_idx, page=back_page)

    tdata = topics[topic_idx]
    title = (tdata.get("title") or "Тема").strip()
    tg_id = (tdata.get("tg_id") or "").strip()
    desc_url = (tdata.get("description") or "").strip() or None
    mind_url = (tdata.get("mindmap_url") or "").strip() or None

    markup = kb_topic_links(desc_url, mind_url, subj_idx, sect_idx, back_page)

    if tg_id:
        media = InputMediaVideo(media=tg_id, caption=title, parse_mode="HTML")
        await edit_or_respawn_media(msg, user_id, media=media, reply_markup=markup, protect_content=True)
        return

    await edit_or_respawn(
        msg, user_id,
        t("topic_no_video").format(title=title),
        markup
    )


# --- callbacks ---

@router.callback_query(F.data == "menu:courses")
async def cb_menu_courses(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    await render_subjects(cb.message, cb.from_user.id, api_client, page=0)


@router.callback_query(F.data.startswith("courses:page:"))
async def cb_courses_page(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    page = int(cb.data.split(":")[-1])
    await render_subjects(cb.message, cb.from_user.id, api_client, page=page)


@router.callback_query(F.data.startswith("courses:open:"))
async def cb_courses_open(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    subj_idx = int(cb.data.split(":")[-1])
    await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0)


@router.callback_query(F.data.startswith("sect:page:"))
async def cb_sections_page(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    _, _, subj_idx, page = cb.data.split(":")
    await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=int(subj_idx), page=int(page))


@router.callback_query(F.data.startswith("sect:back:"))
async def cb_sections_back(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    subj_idx = int(cb.data.split(":")[-1])
    await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0)


@router.callback_query(F.data.startswith("sect:open:"))
async def cb_section_open(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    _, _, subj_idx, sect_idx = cb.data.split(":")
    await render_topics(cb.message, cb.from_user.id, api_client,
                        subj_idx=int(subj_idx), sect_idx=int(sect_idx), page=0)


@router.callback_query(F.data.startswith("sect:locked:"))
async def cb_section_locked(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer(t("section_locked_alert"), show_alert=True)


@router.callback_query(F.data.startswith("topics:page:"))
async def cb_topics_page(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    _, _, subj_idx, sect_idx, page = cb.data.split(":")
    await render_topics(cb.message, cb.from_user.id, api_client,
                        subj_idx=int(subj_idx), sect_idx=int(sect_idx), page=int(page))


@router.callback_query(F.data.startswith("topic:view:"))
async def cb_topic_view(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    _, _, subj_idx, sect_idx, topic_idx, back_page = cb.data.split(":")
    await render_topic_view(cb.message, cb.from_user.id, api_client,
                            subj_idx=int(subj_idx), sect_idx=int(sect_idx),
                            topic_idx=int(topic_idx), back_page=int(back_page))
