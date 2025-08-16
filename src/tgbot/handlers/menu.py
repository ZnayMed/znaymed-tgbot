import contextlib
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.menu_kb import kb_menu_root, kb_subjects

router = Router(name="menu")
log = logging.getLogger(__name__)

PER_PAGE = 9


async def render_menu_root(msg_or_cbmsg):
    try:
        await msg_or_cbmsg.edit_text(t("menu_main"), reply_markup=kb_menu_root(), parse_mode="HTML")
    except Exception:
        # если не можем редактировать (старое сообщение и т.п.) — отправим новое и удалим старое
        chat_id = msg_or_cbmsg.chat.id
        bot = msg_or_cbmsg.bot
        sent = await bot.send_message(chat_id, t("menu_main"), reply_markup=kb_menu_root(), parse_mode="HTML")
        with contextlib.suppress(Exception):
            await msg_or_cbmsg.delete()
        return sent


async def render_courses(msg_or_cbmsg, api: APIGatewayClient, page: int = 0):
    try:
        subjects = await api.get_subjects()
    except Exception:
        return await msg_or_cbmsg.edit_text(t("courses_error"))

    text = t("courses_title") if subjects else t("courses_empty")
    try:
        await msg_or_cbmsg.edit_text(text, reply_markup=kb_subjects(subjects, page=page, per_page=PER_PAGE),
                                     parse_mode="HTML")
    except Exception:
        chat_id = msg_or_cbmsg.chat.id
        bot = msg_or_cbmsg.bot
        sent = await bot.send_message(chat_id, text, reply_markup=kb_subjects(subjects, page=page, per_page=PER_PAGE),
                                      parse_mode="HTML")
        with contextlib.suppress(Exception):
            await msg_or_cbmsg.delete()
        return sent


@router.message(Command("menu"))
async def cmd_menu(msg: Message):
    await msg.answer(t("menu_main"), reply_markup=kb_menu_root(), parse_mode="HTML")


@router.callback_query(F.data == "menu:root")
async def cb_menu_root(cb: CallbackQuery):
    await cb.answer()
    await render_menu_root(cb.message)


@router.callback_query(F.data == "menu:courses")
async def cb_menu_courses(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    await render_courses(cb.message, api_client, page=0)


@router.callback_query(F.data.startswith("courses:page:"))
async def cb_courses_page(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    try:
        page = int(cb.data.split(":")[-1])
    except ValueError:
        page = 0
    await render_courses(cb.message, api_client, page=page)


@router.callback_query(F.data.startswith("courses:open:"))
async def cb_courses_open(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    # пока просто показываем выбранный предмет (дальше привяжем разделы)
    try:
        idx = int(cb.data.split(":")[-1])
        subjects = await api_client.get_subjects()
        title = subjects[idx] if 0 <= idx < len(subjects) else None
        if title:
            await cb.answer(f"Вы выбрали: {title}", show_alert=True)
        else:
            await cb.answer("Элемент не найден.", show_alert=True)
    except Exception:
        await cb.answer("Ошибка загрузки предметов.", show_alert=True)


@router.callback_query(F.data == "menu:pay")
async def cb_menu_pay(cb: CallbackQuery):
    await cb.answer(t("menu_soon"), show_alert=True)
