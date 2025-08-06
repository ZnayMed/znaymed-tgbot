import datetime as dt
import logging
import re

import httpx
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient

log = logging.getLogger(__name__)
router = Router()


class Reg(StatesGroup):
    name = State()
    dob = State()


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
async def cmd_start(msg: Message, api_client: APIGatewayClient, state: FSMContext):
    tg_uid = msg.from_user.id
    try:
        await api_client.get_profile(tg_uid)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # not registered
            await msg.answer(t("start_unregistered"))
            await state.set_state(Reg.name)
            return
        log.exception("Profile check failed")
        await msg.answer(t("api_error"))
        return
    except httpx.HTTPError:
        log.exception("Gateway unreachable")
        await msg.answer(t("api_error"))
        return

    await msg.answer(t("start_registered"))


@router.message(Reg.name)
async def reg_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await msg.answer(t("ask_dob"))
    await state.set_state(Reg.dob)


@router.message(Reg.dob)
async def reg_dob(msg: Message, state: FSMContext, api_client: APIGatewayClient):
    dob = _parse_dob(msg.text)
    if not dob:
        await msg.answer(t("bad_dob"))
        return

    data = await state.get_data()
    name: str = data["name"]
    try:
        await api_client.register_user(str(msg.from_user.id), name, dob.isoformat())
    except httpx.HTTPError:
        log.exception("Registration API failed")
        await msg.answer(t("api_error"))
        return

    await state.clear()
    await msg.answer(t("reg_success"))
