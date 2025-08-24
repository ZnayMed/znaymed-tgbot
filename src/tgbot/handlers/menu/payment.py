import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.payment_kb import kb_pay_root
from .utils import edit_or_respawn

router = Router(name="menu.payment")
log = logging.getLogger(__name__)

PER_PAGE_PAY = 8


async def render_pay_root(msg, user_id: int, api: APIGatewayClient, page: int = 0):
    try:
        subjects = await api.get_subjects()
    except Exception:
        # в случае ошибки всё равно покажем шапку и кнопку "в меню"
        return await edit_or_respawn(msg, user_id, t("pay_error"), kb_pay_root([], page=0))
    return await edit_or_respawn(msg, user_id, t("pay_title"),
                                 kb_pay_root(subjects, page=page, per_page=PER_PAGE_PAY, row_width=1))


@router.callback_query(F.data == "menu:pay")
async def cb_menu_pay(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    await render_pay_root(cb.message, cb.from_user.id, api_client, page=0)


@router.callback_query(F.data.startswith("pay:page:"))
async def cb_pay_page(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    page = int(cb.data.split(":")[-1])
    await render_pay_root(cb.message, cb.from_user.id, api_client, page=page)


@router.callback_query(F.data == "pay:buy:all")
async def cb_pay_buy_all(cb: CallbackQuery):
    # Заглушка оформления
    await cb.answer(t("pay_soon"), show_alert=True)


@router.callback_query(F.data.startswith("pay:subject:"))
async def cb_pay_buy_subject(cb: CallbackQuery, api_client: APIGatewayClient):
    # Заглушка оформления покупки предмета
    await cb.answer(t("pay_soon"), show_alert=True)
