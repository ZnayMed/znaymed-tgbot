import contextlib
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.menu_kb import kb_menu_root, kb_subjects, kb_sections

router = Router(name="menu")
log = logging.getLogger(__name__)

PER_PAGE_SUBJ = 5
PER_PAGE_SECT = 6
MENU_KIND = "menu"


# вспомогательные
async def _send_single_menu(bot, chat_id: int, user_id: int, text: str, reply_markup):
    from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt
    await clean_user_prompts(user_id, bot, kind=MENU_KIND)
    sent = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    await register_prompt(user_id, sent.chat.id, sent.message_id, kind=MENU_KIND)
    return sent


async def _edit_or_respawn(msg, user_id: int, text: str, reply_markup):
    try:
        return await msg.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        with contextlib.suppress(Exception):
            await msg.delete()
        return await _send_single_menu(msg.bot, msg.chat.id, user_id, text, reply_markup)


# рендеры
async def render_menu_root(msg, user_id: int):
    return await _edit_or_respawn(msg, user_id, t("menu_main"), kb_menu_root())


async def render_subjects(msg, user_id: int, api: APIGatewayClient, page: int = 0):
    try:
        subjects = await api.get_subjects()
    except Exception:
        return await _edit_or_respawn(msg, user_id, t("courses_error"), kb_menu_root())
    text = t("courses_title") if subjects else t("courses_empty")
    return await _edit_or_respawn(msg, user_id, text, kb_subjects(subjects, page=page, per_page=PER_PAGE_SUBJ))


async def render_sections(msg, user_id: int, api: APIGatewayClient, subj_idx: int, page: int = 0):
    # получаем название предмета по индексу
    try:
        subjects = await api.get_subjects()
        subject = subjects[subj_idx]
    except Exception:
        return await _edit_or_respawn(msg, user_id, t("sections_error"), kb_menu_root())

    # тянем разделы для пользователя
    try:
        sections = await api.get_subject_sections(user_id, subject)
    except Exception:
        return await _edit_or_respawn(msg, user_id, t("sections_error"), kb_subjects(subjects, page=0))

    text = (t("sections_title").format(subject=subject) if sections else t("sections_empty"))
    return await _edit_or_respawn(
        msg, user_id, text,
        kb_sections(sections, subj_idx=subj_idx, page=page, per_page=PER_PAGE_SECT)
    )


# handlers
@router.message(Command("menu"))
async def cmd_menu(msg: Message):
    await _send_single_menu(msg.bot, msg.chat.id, msg.from_user.id, t("menu_main"), kb_menu_root())


@router.callback_query(F.data == "menu:root")
async def cb_menu_root(cb: CallbackQuery):
    await cb.answer()
    await render_menu_root(cb.message, cb.from_user.id)


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


@router.callback_query(F.data.startswith("sect:open:"))
async def cb_section_open(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    # TODO: тут откроем экран списка тем/видео раздела (следующий шаг)
    _, _, subj_idx, sect_idx = cb.data.split(":")
    try:
        subjects = await api_client.get_subjects()
        subject = subjects[int(subj_idx)]
        sections = await api_client.get_subject_sections(cb.from_user.id, subject)
        title = sections[int(sect_idx)]["title"]
        await cb.answer(f"Открываем: {title}", show_alert=True)
    except Exception:
        await cb.answer("Не удалось открыть раздел.", show_alert=True)


@router.callback_query(F.data.startswith("sect:locked:"))
async def cb_section_locked(cb: CallbackQuery, api_client: APIGatewayClient):
    # Просто показываем окно с предложением купить
    await cb.answer(t("section_locked_alert"), show_alert=True)
