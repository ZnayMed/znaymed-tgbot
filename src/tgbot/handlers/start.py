import datetime as dt
import logging
import re
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.services.redis_client import get_redis
from tgbot.services.reg_prompts import add_prompt
from tgbot.services.registration_service import ensure_not_registered, mute_old_prompts

log = logging.getLogger(__name__)
router = Router(name="start")


class Reg(StatesGroup):
    name = State()
    dob = State()


kb_reg = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="📝 Регистрация", callback_data="reg")]]
)


def _parse_dob(text: str) -> dt.date | None:
    m = re.fullmatch(r"(\d{2})[.](\d{2})[.](\d{4})", text.strip())
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return dt.date(y, mth, d)
    except ValueError:
        return None


@router.message(CommandStart())
async def cmd_start(msg: Message, api_client: APIGatewayClient):
    # Сначала зачистим все старые кнопки (на всякий)
    await mute_old_prompts(msg.from_user.id, msg.bot)

    # Если уже зарегистрирован — сервис сам сообщит пользователю и выйдет
    if not await ensure_not_registered(msg.from_user.id, msg.bot, api_client):
        return

    sent = await msg.answer(t("welcome_register"), reply_markup=kb_reg)
    await add_prompt(get_redis(), msg.from_user.id, sent.chat.id, sent.message_id)


@router.callback_query(F.data == "reg")
async def cb_start_reg(cb: CallbackQuery, state: FSMContext, api_client: APIGatewayClient):
    if not await ensure_not_registered(cb.from_user.id, cb.message.bot, api_client):
        await cb.answer()
        return

    # Гасим клавиатуру у нажатого сообщения
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await cb.answer()

    await state.set_state(Reg.name)
    await cb.message.answer(t("ask_name"))


@router.message(Reg.name)
async def reg_name(msg: Message, state: FSMContext, api_client: APIGatewayClient):
    if not await ensure_not_registered(msg.from_user.id, msg.bot, api_client):
        await state.clear()
        return

    await state.update_data(name=msg.text.strip())
    await state.set_state(Reg.dob)
    await msg.answer(t("ask_dob"), parse_mode="HTML")


@router.message(Reg.dob)
async def reg_dob(msg: Message, state: FSMContext, api_client: APIGatewayClient):
    if not await ensure_not_registered(msg.from_user.id, msg.bot, api_client):
        await state.clear()
        return

    dob = _parse_dob(msg.text)
    if not dob:
        await msg.answer(t("bad_dob_format"))
        return

    data = await state.get_data()
    name: str = data["name"]

    # Регистрация
    await api_client.register_user(msg.from_user.id, name, dob.isoformat())

    # Успех: чистим состояние и все старые кнопки
    await state.clear()
    await mute_old_prompts(msg.from_user.id, msg.bot)
    await msg.answer(t("reg_success"))
