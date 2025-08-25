import contextlib
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.courses_kb import (
    kb_subjects,
    kb_sections,
    kb_topics,
    kb_topic_detail,
)
from .utils import edit_or_respawn


# === ROUTER ===
router = Router(name="menu.courses")
log = logging.getLogger(__name__)


# === CONSTANTS ===
PER_PAGE_SUBJ = 9
PER_PAGE_SECT = 10
PER_PAGE_TOPICS = 8


# === FSM CACHE KEYS ===
SUBJ_KEY = "courses_subjects"   # list[str]
SECT_KEY = "courses_sections"   # dict[str(subj_idx) -> list[dict]]
TOPIC_KEY = "courses_topics"    # dict[str(section_title) -> list[dict]]


# === UTILS: PAGER ===
def _clamp_page(total: int, per_page: int, page: int) -> int:
    if total <= 0:
        return 0

    last = (total - 1) // per_page
    if page < 0:
        return 0
    if page > last:
        return last
    return page


# === UTILS: CACHE ===
async def _clear_courses_cache(state: FSMContext) -> None:
    # Сбрасываем весь кэш раздела «Курсы» при входе
    await state.update_data(**{SUBJ_KEY: None, SECT_KEY: None, TOPIC_KEY: None})


async def _get_subjects_cached(state: FSMContext, api: APIGatewayClient) -> list[str]:
    data = await state.get_data()
    subjects = data.get(SUBJ_KEY)

    if isinstance(subjects, list) and subjects:
        return subjects

    subjects = await api.get_subjects()
    await state.update_data(**{SUBJ_KEY: subjects})
    return subjects


async def _get_sections_cached(
    state: FSMContext, api: APIGatewayClient, user_id: int, subj_idx: int
) -> tuple[str, list[dict]]:
    data = await state.get_data()
    subjects: list[str] = await _get_subjects_cached(state, api)

    if not (0 <= subj_idx < len(subjects)):
        return "", []

    subject = subjects[subj_idx]

    sect_cache: dict = data.get(SECT_KEY) or {}
    key = str(subj_idx)
    sections = sect_cache.get(key)

    if isinstance(sections, list):
        return subject, sections

    sections = await api.get_subject_sections(user_id, subject)
    sect_cache[key] = sections
    await state.update_data(**{SECT_KEY: sect_cache})
    return subject, sections


async def _get_topics_cached(state: FSMContext, api: APIGatewayClient, section_title: str) -> list[dict]:
    data = await state.get_data()
    topics_cache: dict = data.get(TOPIC_KEY) or {}
    topics = topics_cache.get(section_title)

    if isinstance(topics, list):
        return topics

    payload = await api.get_section_topics(section_title)
    topics = list(payload.get("topics") or [])
    topics_cache[section_title] = topics
    await state.update_data(**{TOPIC_KEY: topics_cache})
    return topics


# === RENDER: SUBJECTS ===
async def render_subjects(msg, user_id: int, api: APIGatewayClient, page: int = 0, state: FSMContext | None = None):
    try:
        subjects = await _get_subjects_cached(state, api) if state else await api.get_subjects()
    except Exception:
        return await edit_or_respawn(msg, user_id, t("courses_error"), kb_subjects([], page=0))

    page = _clamp_page(len(subjects), PER_PAGE_SUBJ, page)
    text = t("courses_title") if subjects else t("courses_empty")

    return await edit_or_respawn(
        msg, user_id, text,
        kb_subjects(subjects, page=page, per_page=PER_PAGE_SUBJ),
    )


# === RENDER: SECTIONS ===
async def render_sections(
    msg, user_id: int, api: APIGatewayClient, subj_idx: int, page: int = 0, state: FSMContext | None = None
):
    try:
        subject, sections = await _get_sections_cached(state, api, user_id, subj_idx)
        if not subject:
            raise IndexError("bad subj_idx")
    except Exception:
        subjects = await _get_subjects_cached(state, api)
        return await edit_or_respawn(msg, user_id, t("sections_error"), kb_subjects(subjects, page=0))

    page = _clamp_page(len(sections), PER_PAGE_SECT, page)
    text = t("sections_title").format(subject=subject) if sections else t("sections_empty")

    return await edit_or_respawn(
        msg, user_id, text,
        kb_sections(sections, subj_idx=subj_idx, page=page, per_page=PER_PAGE_SECT),
    )


# === RENDER: TOPICS ===
async def render_topics(
    msg, user_id: int, api: APIGatewayClient, subj_idx: int, sect_idx: int, page: int = 0, state: FSMContext | None = None
):
    subject, sections = await _get_sections_cached(state, api, user_id, subj_idx)

    if not (0 <= sect_idx < len(sections)):
        return await edit_or_respawn(
            msg, user_id, t("topics_error"),
            kb_sections(sections, subj_idx=subj_idx, page=0),
        )

    section_title = sections[sect_idx]["title"]

    try:
        topics = await _get_topics_cached(state, api, section_title)
    except Exception:
        return await edit_or_respawn(
            msg, user_id, t("topics_error"),
            kb_sections(sections, subj_idx=subj_idx, page=0),
        )

    page = _clamp_page(len(topics), PER_PAGE_TOPICS, page)
    text = t("topics_title").format(section=section_title) if topics else t("topics_empty")

    return await edit_or_respawn(
        msg, user_id, text,
        kb_topics(topics, subj_idx=subj_idx, sect_idx=sect_idx, page=page, per_page=PER_PAGE_TOPICS),
    )


# === RENDER: TOPIC VIEW ===
async def render_topic_view(
    msg, user_id: int, api: APIGatewayClient,
    subj_idx: int, sect_idx: int, topic_idx: int, back_page: int,
    state: FSMContext | None = None
):
    subject, sections = await _get_sections_cached(state, api, user_id, subj_idx)

    if not (0 <= sect_idx < len(sections)):
        return await render_sections(msg, user_id, api, subj_idx=subj_idx, page=0, state=state)

    section_title = sections[sect_idx]["title"]
    topics = await _get_topics_cached(state, api, section_title)

    if not (0 <= topic_idx < len(topics)):
        return await render_topics(msg, user_id, api, subj_idx, sect_idx, page=back_page, state=state)

    tdata = topics[topic_idx]
    title = tdata.get("title") or "Тема"
    desc = tdata.get("description") or "Без описания."
    tg_id = tdata.get("tg_id") or ""
    mind = tdata.get("mindmap_url") or None

    text = t("topic_view_title").format(title=title, desc=desc)
    has_video = bool(tg_id)

    return await edit_or_respawn(
        msg, user_id, text,
        kb_topic_detail(has_video, mind, subj_idx, sect_idx, topic_idx, back_page),
    )


# === CALLBACKS: ROOT ===
@router.callback_query(F.data == "menu:courses")
async def cb_menu_courses(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()

    # Сбрасываем и прогреваем кэш
    await _clear_courses_cache(state)
    _ = await _get_subjects_cached(state, api_client)

    await render_subjects(cb.message, cb.from_user.id, api_client, page=0, state=state)


# === CALLBACKS: SUBJECTS ===
@router.callback_query(F.data.startswith("courses:page:"))
async def cb_courses_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    raw_page = int(cb.data.split(":")[-1])

    subjects = await _get_subjects_cached(state, api_client)
    page = _clamp_page(len(subjects), PER_PAGE_SUBJ, raw_page)

    await render_subjects(cb.message, cb.from_user.id, api_client, page=page, state=state)


@router.callback_query(F.data.startswith("courses:open:"))
async def cb_courses_open(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    subj_idx = int(cb.data.split(":")[-1])

    # Прогреем кэш разделов
    await _get_sections_cached(state, api_client, cb.from_user.id, subj_idx)
    await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0, state=state)


# === CALLBACKS: SECTIONS ===
@router.callback_query(F.data.startswith("sect:page:"))
async def cb_sections_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, raw_page = cb.data.split(":")
    subj_idx, raw_page = int(subj_idx), int(raw_page)

    _subject, sections = await _get_sections_cached(state, api_client, cb.from_user.id, subj_idx)
    page = _clamp_page(len(sections), PER_PAGE_SECT, raw_page)

    await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=page, state=state)


@router.callback_query(F.data.startswith("sect:back:"))
async def cb_sections_back(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    subj_idx = int(cb.data.split(":")[-1])

    await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0, state=state)


@router.callback_query(F.data.startswith("sect:open:"))
async def cb_section_open(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, sect_idx = cb.data.split(":")
    subj_idx, sect_idx = int(subj_idx), int(sect_idx)

    subject, sections = await _get_sections_cached(state, api_client, cb.from_user.id, subj_idx)
    if not (0 <= sect_idx < len(sections)):
        return await render_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0, state=state)

    section_title = sections[sect_idx]["title"]

    # Прогреем кэш тем
    _ = await _get_topics_cached(state, api_client, section_title)
    await render_topics(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, sect_idx=sect_idx, page=0, state=state)


@router.callback_query(F.data.startswith("sect:locked:"))
async def cb_section_locked(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer(t("section_locked_alert"), show_alert=True)


# === CALLBACKS: TOPICS ===
@router.callback_query(F.data.startswith("topics:page:"))
async def cb_topics_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, sect_idx, raw_page = cb.data.split(":")
    subj_idx, sect_idx, raw_page = int(subj_idx), int(sect_idx), int(raw_page)

    _subject, sections = await _get_sections_cached(state, api_client, cb.from_user.id, subj_idx)
    if not (0 <= sect_idx < len(sections)):
        return

    section_title = sections[sect_idx]["title"]
    topics = await _get_topics_cached(state, api_client, section_title)
    page = _clamp_page(len(topics), PER_PAGE_TOPICS, raw_page)

    await render_topics(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, sect_idx=sect_idx, page=page, state=state)


@router.callback_query(F.data.startswith("topic:view:"))
async def cb_topic_view(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, sect_idx, topic_idx, back_page = cb.data.split(":")
    await render_topic_view(
        cb.message, cb.from_user.id, api_client,
        subj_idx=int(subj_idx), sect_idx=int(sect_idx),
        topic_idx=int(topic_idx), back_page=int(back_page), state=state,
    )


# === CALLBACKS: TOPIC VIDEO ===
@router.callback_query(F.data.startswith("topic:video:"))
async def cb_topic_video(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, sect_idx, topic_idx, _ = cb.data.split(":")
    si, ci, ti = int(subj_idx), int(sect_idx), int(topic_idx)

    # Всё из кэша текущей сессии «Курсы»
    subject, sections = await _get_sections_cached(state, api_client, cb.from_user.id, si)
    if not (0 <= ci < len(sections)):
        return

    section_title = sections[ci]["title"]
    topics = await _get_topics_cached(state, api_client, section_title)
    if not (0 <= ti < len(topics)):
        return

    tg_id = topics[ti].get("tg_id") or ""
    if not tg_id:
        return

    ok = True
    try:
        await cb.message.bot.send_video(cb.message.chat.id, tg_id)
    except Exception:
        ok = False

    if not ok:
        with contextlib.suppress(Exception):
            await cb.message.bot.send_document(cb.message.chat.id, tg_id)
