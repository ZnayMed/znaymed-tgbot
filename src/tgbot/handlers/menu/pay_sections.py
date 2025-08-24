import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.payment_kb import kb_pay_sections_subjects, kb_pay_sections_list
from .utils import edit_or_respawn

router = Router(name="menu.pay.sections")
log = logging.getLogger(__name__)

PER_PAGE_SUBJ = 9
PER_PAGE_SECT = 10


class PaySec(StatesGroup):
    # Один «плоский» стейт для потока выбора разделов.
    flow = State()


_SEP = "\x1f"  # unit separator — маловероятен в названиях


def _encode(subject: str, section_title: str) -> str:
    return f"{subject}{_SEP}{section_title}"


def _decode(item: str) -> tuple[str, str]:
    subj, title = item.split(_SEP, 1)
    return subj, title


async def _get_cart(state: FSMContext) -> set[str]:
    data = await state.get_data()
    return set(data.get("cart", []))


async def _set_cart(state: FSMContext, cart: set[str]) -> None:
    await state.update_data(cart=list(cart))


async def _toggle_cart(state: FSMContext, subject: str, section_title: str) -> bool:
    """
    True -> стало добавлено, False -> удалено
    """
    cart = await _get_cart(state)
    key = _encode(subject, section_title)
    if key in cart:
        cart.remove(key)
        await _set_cart(state, cart)
        return False
    cart.add(key)
    await _set_cart(state, cart)
    return True


async def render_paysec_subjects(msg, user_id: int, api: APIGatewayClient, page: int = 0,
                                 state: FSMContext | None = None):
    subjects = await api.get_subjects()
    cart_n = 0
    if state is not None:
        data = await state.get_data()
        cart_n = len(data.get("cart", []))
    return await edit_or_respawn(
        msg, user_id, t("pay_sections_title"),
        kb_pay_sections_subjects(subjects, page=page, per_page=PER_PAGE_SUBJ, row_width=2, cart_count=cart_n)
    )


async def render_paysec_sections(msg, user_id: int, api: APIGatewayClient, subj_idx: int, page: int,
                                 state: FSMContext):
    subjects = await api.get_subjects()
    subject = subjects[subj_idx]
    sections = await api.get_subject_sections(user_id, subject)
    locked = [s for s in sections if not bool(s.get("accessible"))]  # только закрытые

    selected = await _get_cart(state)
    cart_n = len(selected)

    text = t("pay_sections_list_title").format(subject=subject) if locked else t("pay_sections_empty")
    return await edit_or_respawn(
        msg, user_id, text,
        kb_pay_sections_list(
            subject=subject,
            sections_locked=locked,
            selected_keys=selected,
            encode_fn=lambda subj, title: _encode(subj, title),
            subj_idx=subj_idx,
            page=page,
            per_page=PER_PAGE_SECT,
            row_width=2,
            cart_count=cart_n
        )
    )


# Вход в под-режим «Конкретные разделы» — создаём пустую корзину в FSM
@router.callback_query(F.data == "pay:sections")
async def cb_pay_sections_root(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await state.set_state(PaySec.flow)
    await _set_cart(state, set())
    await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=0, state=state)


# Листание предметов
@router.callback_query(F.data.startswith("paysec:page:"))
async def cb_paysec_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    page = int(cb.data.split(":")[-1])
    await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=page, state=state)


# Переход к списку разделов конкретного предмета
@router.callback_query(F.data.startswith("paysec:open:"))
async def cb_paysec_open_subject(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    subj_idx = int(cb.data.split(":")[-1])
    await render_paysec_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0, state=state)


# Листание разделов выбранного предмета
@router.callback_query(F.data.startswith("paysec:sectpage:"))
async def cb_paysec_sections_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, page = cb.data.split(":")
    await render_paysec_sections(cb.message, cb.from_user.id, api_client,
                                 subj_idx=int(subj_idx), page=int(page), state=state)


# Тоггл раздела в корзине
@router.callback_query(F.data.startswith("paysec:toggle:"))
async def cb_paysec_toggle(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, sect_idx, page = cb.data.split(":")
    subj_idx = int(subj_idx);
    sect_idx = int(sect_idx);
    page = int(page)

    # subject + section
    subjects = await api_client.get_subjects()
    subject = subjects[subj_idx]
    sections = await api_client.get_subject_sections(cb.from_user.id, subject)
    locked = [s for s in sections if not bool(s.get("accessible"))]
    if not (0 <= sect_idx < len(locked)):
        return

    title = locked[sect_idx]["title"]
    await _toggle_cart(state, subject, title)

    # Ререндер текущей страницы (с учётом обновлённой корзины)
    await render_paysec_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=page, state=state)


# Чекаут — пока заглушка
@router.callback_query(F.data == "paysec:checkout")
async def cb_paysec_checkout(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    n = len(await _get_cart(state))
    if n <= 0:
        await cb.answer("Корзина пуста.", show_alert=True)
        return
    await cb.answer(t("pay_checkout_soon").format(n=n), show_alert=True)


# Назад к списку предметов (внутри под-режима) — корзину НЕ сбрасываем
@router.callback_query(F.data == "paysec:subjects")
async def cb_paysec_subjects(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=0, state=state)


# Выход в экран оплаты — корзину сбрасываем (очистка FSM)
@router.callback_query(F.data == "paysec:exit")
async def cb_paysec_exit(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await state.clear()
    # ленивый импорт, чтобы не ловить циклические зависимости
    from .payment import render_pay_root
    await render_pay_root(cb.message, cb.from_user.id, api_client, page=0)


# Выход в главное меню — корзину сбрасываем (очистка FSM)
@router.callback_query(F.data == "paysec:exit_menu")
async def cb_paysec_exit_menu(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    from .root import render_menu_root
    await render_menu_root(cb.message, cb.from_user.id)


@router.callback_query(F.data == "paysec:nop")
async def cb_paysec_nop(cb: CallbackQuery):
    await cb.answer()
