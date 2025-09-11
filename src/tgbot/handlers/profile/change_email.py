import re
import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient

router = Router(name="profile.change_email")
log = logging.getLogger(__name__)


class ChangeEmailFlow(StatesGroup):
    email = State()


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _parse_email(text: str) -> str | None:
    s = (text or "").strip()
    return s.lower() if s and _EMAIL_RE.fullmatch(s) else None


@router.message(Command("change_email"))
async def cmd_change_email(msg: Message, state: FSMContext):
    await state.set_state(ChangeEmailFlow.email)
    await msg.answer(t("email_change_ask"), parse_mode="HTML")


@router.callback_query(F.data == "profile:change_email")
async def cb_change_email(cb: CallbackQuery, state: FSMContext):
    try:
        await cb.answer()
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await state.set_state(ChangeEmailFlow.email)
    await cb.message.answer(t("email_change_ask"), parse_mode="HTML")


@router.message(ChangeEmailFlow.email)
async def change_email_input(msg: Message, state: FSMContext, api_client: APIGatewayClient):
    email = _parse_email(msg.text)
    if not email:
        await msg.answer(t("email_change_invalid"))
        return

    try:
        resp = await api_client.change_email(msg.from_user.id, email)
    except Exception as e:
        log.exception("change_email API call failed: %s", e)
        await msg.answer(t("api_error"))
        return

    if resp.get("success"):
        await state.clear()
        await msg.answer(t("email_change_success"))
    else:
        # дружелюбный маппинг типовых сообщений
        msg_text = resp.get("message") or t("email_change_fail")
        if "invalid email" in msg_text.lower():
            msg_text = t("email_change_invalid")
        await msg.answer(msg_text)
