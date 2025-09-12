import logging
import re
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from tgbot.keyboards.start_kb import kb_reg
from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.services.redis_client import get_redis
from tgbot.services.registration_service import ensure_not_registered
from tgbot.services.user_cache import cache_registered

from tgbot.utils.prompt_cleaner import clean_user_prompts, register_prompt

router = Router(name="start")
log = logging.getLogger(__name__)


class Reg(StatesGroup):
    name = State()
    email = State()


_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)


def _parse_email(text: str) -> str | None:
    s = (text or "").strip()
    if not s:
        return None
    if _EMAIL_RE.fullmatch(s):
        return s.lower()
    return None


@router.message(CommandStart())
async def cmd_start(msg: Message, api_client: APIGatewayClient):
    await clean_user_prompts(msg.from_user.id, msg.bot, kind="reg")

    if not await ensure_not_registered(msg.from_user.id, msg.bot, api_client):
        # Уже зарегистрирован → ничего не спрашиваем
        return

    sent = await msg.answer(t("welcome_register"), reply_markup=kb_reg())
    await register_prompt(msg.from_user.id, sent.chat.id, sent.message_id, kind="reg")


@router.callback_query(F.data == "reg")
async def cb_start_reg(cb: CallbackQuery, state: FSMContext, api_client: APIGatewayClient):
    if not await ensure_not_registered(cb.from_user.id, cb.message.bot, api_client):
        await cb.answer()
        return

    # Гасим клавиатуру
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

    await state.update_data(name=(msg.text or "").strip())
    await state.set_state(Reg.email)
    await msg.answer(t("ask_email"), parse_mode="HTML")


@router.message(Reg.email)
async def reg_email(msg: Message, state: FSMContext, api_client: APIGatewayClient):
    if not await ensure_not_registered(msg.from_user.id, msg.bot, api_client):
        await state.clear()
        return

    email = _parse_email(msg.text)
    if not email:
        await msg.answer(t("reg_tech_error"))
        return

    data = await state.get_data()
    name: str = (data.get("name") or "").strip()

    try:
        resp = await api_client.register_user(msg.from_user.id, name, email)
    except Exception:
        await msg.answer(t("reg_tech_error"))
        return

    if not resp or not resp.get("success"):
        await msg.answer(t("reg_tech_error"))
        return

    r = get_redis()
    await cache_registered(r, msg.from_user.id)
    await state.clear()
    await clean_user_prompts(msg.from_user.id, msg.bot, kind="reg")

    sections: list[str] = []
    if resp.get("grant_success") and resp.get("granted_section"):
        sections.append(str(resp["granted_section"]))

    if sections:
        sections_note = t("reg_sections_note").format(sections=", ".join(sections))
    else:
        sections_note = ""

    await msg.answer(t("reg_success").format(sections_note=sections_note), parse_mode="HTML")