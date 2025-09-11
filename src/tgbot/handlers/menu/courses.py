import contextlib
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.courses_kb import kb_subjects, kb_sections, kb_topics, kb_topic_detail, kb_topic_links
from .utils import edit_or_respawn

router = Router(name="menu.courses")
log = logging.getLogger(__name__)

PER_PAGE_SUBJ = 9
PER_PAGE_SECT = 10
PER_PAGE_TOPICS = 8


async def render_subjects(msg, user_id: int, api: APIGatewayClient, page: int = 0):
    try:
        subjects = await api.get_subjects()
    except Exception:
        # покажем ошибку и простую клаву «назад в меню» через пустой список
        return await edit_or_respawn(msg, user_id, t("courses_error"), kb_subjects([], page=0))
    text = t("courses_title") if subjects else t("courses_empty")
    return await edit_or_respawn(msg, user_id, text,
                                 kb_subjects(subjects, page=page, per_page=PER_PAGE_SUBJ))


async def render_sections(msg, user_id: int, api: APIGatewayClient, subj_idx: int, page: int = 0):
    try:
        subjects = await api.get_subjects()
        subject = subjects[subj_idx]
    except Exception:
        return await edit_or_respawn(msg, user_id, t("sections_error"),
                                     kb_subjects(await api.get_subjects(), page=0))
    try:
        sections = await api.get_subject_sections(user_id, subject)
    except Exception:
        return await edit_or_respawn(msg, user_id, t("sections_error"),
                                     kb_subjects(await api.get_subjects(), page=0))
    text = t("sections_title").format(subject=subject) if sections else t("sections_empty")
    return await edit_or_respawn(msg, user_id, text,
                                 kb_sections(sections, subj_idx=subj_idx, page=page, per_page=PER_PAGE_SECT))


async def render_topics(msg, user_id: int, api: APIGatewayClient, subj_idx: int, sect_idx: int, page: int = 0):
    subjects = await api.get_subjects()
    subject = subjects[subj_idx]
    sections = await api.get_subject_sections(user_id, subject)
    if not (0 <= sect_idx < len(sections)):
        return await edit_or_respawn(msg, user_id, t("topics_error"),
                                     kb_sections(sections, subj_idx=subj_idx, page=0))
    section_title = sections[sect_idx]["title"]
    try:
        payload = await api.get_section_topics(section_title)
        topics = list(payload.get("topics") or [])
    except Exception:
        return await edit_or_respawn(msg, user_id, t("topics_error"),
                                     kb_sections(sections, subj_idx=subj_idx, page=0))
    text = t("topics_title").format(section=section_title) if topics else t("topics_empty")
    return await edit_or_respawn(msg, user_id, text,
                                 kb_topics(topics, subj_idx=subj_idx, sect_idx=sect_idx,
                                           page=page, per_page=PER_PAGE_TOPICS))


async def render_topic_view(msg, user_id: int, api: APIGatewayClient,
                            subj_idx: int, sect_idx: int, topic_idx: int, back_page: int):
    subjects = await api.get_subjects()
    subject = subjects[subj_idx]
    sections = await api.get_subject_sections(user_id, subject)
    if not (0 <= sect_idx < len(sections)):
        return await render_sections(msg, user_id, api, subj_idx=subj_idx, page=0)

    section_title = sections[sect_idx]["title"]

    data = await api.get_section_topics(section_title)
    topics = list(data.get("topics") or [])
    if not (0 <= topic_idx < len(topics)):
        return await render_topics(msg, user_id, api, subj_idx, sect_idx, page=back_page)

    tdata = topics[topic_idx]
    title = tdata.get("title") or "Тема"
    tg_id = (tdata.get("tg_id") or "").strip()
    desc_url = (tdata.get("description") or "").strip() or None
    mind_url = (tdata.get("mindmap_url") or "").strip() or None

    # Клава под видео/сообщением
    markup = kb_topic_links(desc_url, mind_url, subj_idx, sect_idx, back_page)

    # Если есть видео — отправляем его с подписью = название темы
    if tg_id:
        sent = False
        try:
            await msg.bot.send_video(
                chat_id=msg.chat.id,
                video=tg_id,
                caption=title,  # название темы
                reply_markup=markup,
                protect_content=True,
            )
            sent = True
        except Exception:
            with contextlib.suppress(Exception):
                await msg.bot.send_document(
                    chat_id=msg.chat.id,
                    document=tg_id,
                    caption=title,
                    reply_markup=markup,
                    protect_content=True,
                )
                sent = True

        if not sent:
            # Если совсем не получилось — просто текст с кнопками
            await msg.bot.send_message(
                chat_id=msg.chat.id,
                text=t("topic_video_error").format(title=title),
                reply_markup=markup,
                protect_content=True,
            )
        return

    # Если видео нет — честно сообщаем и даем ссылки/навигацию
    await msg.bot.send_message(
        chat_id=msg.chat.id,
        text=t("topic_no_video").format(title=title),
        reply_markup=markup,
        protect_content=True,
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
