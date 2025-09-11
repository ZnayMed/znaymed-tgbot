import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.payment_kb import (
    kb_pay_sections_subjects,
    kb_pay_sections_list,
    kb_pay_cart,
)
from tgbot.utils.edit_or_respawn import edit_or_respawn
from ...utils.safe_answer import safe_answer

# === ROUTER ===
router = Router(name="menu.pay.sections")
log = logging.getLogger(__name__)

# === CONSTANTS ===
PER_PAGE_SUBJ = 9
PER_PAGE_SECT = 10
_SEP = "\x1f"


# === FSM ===
class PaySec(StatesGroup):
    flow = State()


# === UTILS: ENCODE / DECODE ===
def _encode(subject: str, section_title: str) -> str:
    return f"{subject}{_SEP}{section_title}"


def _decode(item: str) -> tuple[str, str]:
    subj, title = item.split(_SEP, 1)
    return subj, title


# === UTILS: CART ===
async def _get_cart(state: FSMContext) -> set[str]:
    data = await state.get_data()
    return set(data.get("cart", []))


async def _set_cart(state: FSMContext, cart: set[str]) -> None:
    await state.update_data(cart=list(cart))


async def _toggle_cart(state: FSMContext, subject: str, section_title: str) -> bool:
    cart = await _get_cart(state)
    key = _encode(subject, section_title)

    if key in cart:
        cart.remove(key)
        await _set_cart(state, cart)
        return False

    cart.add(key)
    await _set_cart(state, cart)
    return True


# === UTILS: CACHE ===
async def _get_subjects_cached(state: FSMContext, api: APIGatewayClient) -> list[str]:
    data = await state.get_data()
    subjects = data.get("subjects")

    if isinstance(subjects, list) and subjects:
        return subjects

    subjects = await api.get_subjects()
    await state.update_data(subjects=subjects)
    return subjects


async def _set_current_subject(state: FSMContext, subj_idx: int, subject: str) -> None:
    await state.update_data(subj_idx=subj_idx, subject=subject, sections_locked=None)


async def _get_current_subject(state: FSMContext) -> tuple[int | None, str | None]:
    data = await state.get_data()
    return data.get("subj_idx"), data.get("subject")


async def _get_locked_sections_cached(
        state: FSMContext, api: APIGatewayClient, user_id: int, subject: str
) -> list[dict]:
    data = await state.get_data()
    cached_subject = data.get("subject")
    locked = data.get("sections_locked") if cached_subject == subject else None

    if isinstance(locked, list):
        return locked

    sections = await api.get_subject_sections(user_id, subject)
    locked = [s for s in sections if not bool(s.get("accessible"))]
    await state.update_data(sections_locked=locked)
    return locked


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


# === RENDER: SUBJECTS ===
async def render_paysec_subjects(
        msg, user_id: int, api: APIGatewayClient, page: int = 0, state: FSMContext | None = None
):
    subjects = (
        await _get_subjects_cached(state, api)
        if state else await api.get_subjects()
    )

    cart_n = 0
    if state is not None:
        data = await state.get_data()
        cart_n = len(data.get("cart", []))

    page = _clamp_page(len(subjects), PER_PAGE_SUBJ, page)

    return await edit_or_respawn(
        msg,
        user_id,
        t("pay_sections_title"),
        kb_pay_sections_subjects(
            subjects,
            page=page,
            per_page=PER_PAGE_SUBJ,
            row_width=3,
            cart_count=cart_n,
        ),
    )


async def render_paysec_sections(
        msg, user_id: int, api: APIGatewayClient, subj_idx: int, page: int, state: FSMContext
):
    # 1) subject из кэша
    subjects = await _get_subjects_cached(state, api)
    if not (0 <= subj_idx < len(subjects)):
        return await render_paysec_subjects(msg, user_id, api, page=0, state=state)

    subject = subjects[subj_idx]

    # 2) сохранить текущий subject
    cur_idx, cur_subject = await _get_current_subject(state)
    if cur_idx != subj_idx or cur_subject != subject:
        await _set_current_subject(state, subj_idx, subject)

    # 3) locked разделы
    locked = await _get_locked_sections_cached(state, api, user_id, subject)

    # 4) корзина
    selected = await _get_cart(state)
    cart_n = len(selected)

    # 5) рендер
    page = _clamp_page(len(locked), PER_PAGE_SECT, page)
    text = (
        t("pay_sections_list_title").format(subject=subject)
        if locked else t("pay_sections_empty")
    )

    return await edit_or_respawn(
        msg,
        user_id,
        text,
        kb_pay_sections_list(
            subject=subject,
            sections_locked=locked,
            selected_keys=selected,
            encode_fn=lambda subj, title: _encode(subj, title),
            subj_idx=subj_idx,
            page=page,
            per_page=PER_PAGE_SECT,
            row_width=2,
            cart_count=cart_n,
        ),
    )


# === CALLBACKS: ROOT ===
@router.callback_query(F.data == "pay:sections")
async def cb_pay_sections_root(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await state.set_state(PaySec.flow)
    await _set_cart(state, set())

    subjects = await api_client.get_subjects()
    await state.update_data(subjects=subjects, subj_idx=None, subject=None, sections_locked=None)

    await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=0, state=state)


# === CALLBACKS: PAGINATION (SUBJECTS) ===
@router.callback_query(F.data.startswith("paysec:page:"))
async def cb_paysec_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    raw_page = int(cb.data.split(":")[-1])
    subjects = await _get_subjects_cached(state, api_client)
    page = _clamp_page(len(subjects), PER_PAGE_SUBJ, raw_page)

    await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=page, state=state)


# === CALLBACKS: OPEN SUBJECT ===
@router.callback_query(F.data.startswith("paysec:open:"))
async def cb_paysec_open_subject(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    subj_idx = int(cb.data.split(":")[-1])

    subjects = await _get_subjects_cached(state, api_client)
    if not (0 <= subj_idx < len(subjects)):
        return await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=0, state=state)

    subject = subjects[subj_idx]

    await _set_current_subject(state, subj_idx, subject)

    locked = await api_client.get_subject_sections(cb.from_user.id, subject)
    locked = [s for s in locked if not bool(s.get("accessible"))]
    await state.update_data(sections_locked=locked)

    await render_paysec_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=0, state=state)


# === CALLBACKS: PAGINATION (SECTIONS) ===
@router.callback_query(F.data.startswith("paysec:sectpage:"))
async def cb_paysec_sections_page(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, raw_page = cb.data.split(":")
    subj_idx, raw_page = int(subj_idx), int(raw_page)

    data = await state.get_data()
    locked = data.get("sections_locked") or []
    page = _clamp_page(len(locked), PER_PAGE_SECT, raw_page)

    await render_paysec_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=page, state=state)


# === CALLBACKS: TOGGLE SECTION ===
@router.callback_query(F.data.startswith("paysec:toggle:"))
async def cb_paysec_toggle(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    _, _, subj_idx, sect_idx, raw_page = cb.data.split(":")
    subj_idx, sect_idx, raw_page = int(subj_idx), int(sect_idx), int(raw_page)

    data = await state.get_data()
    subjects = data.get("subjects") or []
    if not (0 <= subj_idx < len(subjects)):
        return

    subject = subjects[subj_idx]
    locked = data.get("sections_locked") or []
    if not (0 <= sect_idx < len(locked)):
        return

    title = locked[sect_idx].get("title", "")
    await _toggle_cart(state, subject, title)

    page = _clamp_page(len(locked), PER_PAGE_SECT, raw_page)
    await render_paysec_sections(cb.message, cb.from_user.id, api_client, subj_idx=subj_idx, page=page, state=state)


# === CALLBACKS: CHECKOUT ===
@router.callback_query(F.data == "paysec:checkout")
async def cb_paysec_checkout(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()

    data = await state.get_data()
    raw = list(data.get("cart", []))

    decoded: list[tuple[str, str]] = []
    for key in raw:
        try:
            subj, sec = key.split(_SEP, 1)
        except Exception:
            continue
        decoded.append((subj, sec))

    if not decoded:
        await cb.answer(t("pay_cart_empty"), show_alert=True)
        return

    sections = sorted({sec for _, sec in decoded})

    try:
        resp = await api_client.create_payment_sections(cb.from_user.id, sections)
    except Exception as e:
        log.exception("Create payment failed: %s", e)
        await cb.answer(t("pay_create_failed"), show_alert=True)
        return

    missing = list(resp.get("missing_sections") or [])
    total = int(resp.get("total_kopeck", 0))
    if total <= 0 or len(missing) == 0:
        await cb.answer(t("pay_nothing_to_buy"), show_alert=True)
        return

    payment_id = str(resp.get("payment_id", ""))
    payment_url = str(resp.get("payment_url", ""))
    currency = str(resp.get("currency", "RUB"))
    status = str(resp.get("status", ""))

    if not payment_url:
        await cb.answer(t("pay_missing_url"), show_alert=True)
        return

    from .payment import render_payment_screen
    await render_payment_screen(
        cb.message,
        cb.from_user.id,
        payment_id=payment_id,
        payment_url=payment_url,
        total_kopeck=total,
        currency=currency,
        missing_sections=missing,
    )


# === CALLBACKS: NAVIGATION ===
@router.callback_query(F.data == "paysec:subjects")
async def cb_paysec_subjects(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await render_paysec_subjects(cb.message, cb.from_user.id, api_client, page=0, state=state)


@router.callback_query(F.data == "paysec:exit")
async def cb_paysec_exit(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await state.clear()
    from .payment import render_pay_root
    await render_pay_root(cb.message, cb.from_user.id, api_client, page=0)


@router.callback_query(F.data == "paysec:exit_menu")
async def cb_paysec_exit_menu(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    from .root import render_menu_root
    await render_menu_root(cb.message, cb.from_user.id)


@router.callback_query(F.data == "paysec:nop")
async def cb_paysec_nop(cb: CallbackQuery):
    await cb.answer()


# === RENDER: CART ===
async def render_paysec_cart(msg, user_id: int, api_client: APIGatewayClient, state: FSMContext, page: int = 0):
    data = await state.get_data()
    raw = list(data.get("cart", []))

    decoded: list[tuple[str, str]] = []
    for key in raw:
        try:
            subj, sec = key.split(_SEP, 1)
        except Exception:
            continue
        decoded.append((subj, sec))

    decoded.sort(key=lambda x: (x[0].lower(), x[1].lower()))

    total_text: str | None = None
    if decoded:
        try:
            # серверу нужны только названия секций; на всякий случай уберём дубли
            sections = sorted({sec for _, sec in decoded})
            resp = await api_client.get_sections_total(user_id, sections)
            kopeck = int(resp.get("total_kopeck", 0))
            currency = str(resp.get("currency", "RUB"))

            # простое форматирование RUB: 1234.50 ₽
            rub = kopeck // 100
            kop = kopeck % 100
            curr_symbol = "₽" if currency.upper() in {"RUB", "RUR", "RUBLE", "RUBLES",
                                                      "RU"} or currency == "₽" else currency
            total_text = f"{rub}.{kop:02d} {curr_symbol}"
        except Exception as e:
            log.exception("Failed to get sections total: %s", e)
            total_text = None

    title = (
        t("pay_cart_title").format(n=len(decoded))
        if decoded else t("pay_cart_empty")
    )

    return await edit_or_respawn(
        msg,
        user_id,
        title,
        kb_pay_cart(decoded, page=page, per_page=6, row_width=2, total_text=total_text),
    )


# === CALLBACKS: CART ===
@router.callback_query(F.data == "paysec:cart")
async def cb_paysec_cart(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await render_paysec_cart(cb.message, cb.from_user.id, api_client, state, page=0)


@router.callback_query(F.data.startswith("paysec:cartpage:"))
async def cb_paysec_cartpage(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    page = int(cb.data.split(":")[-1])
    await render_paysec_cart(cb.message, cb.from_user.id, api_client, state, page=page)


@router.callback_query(F.data.startswith("paysec:cartremove:"))
async def cb_paysec_cartremove(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await safe_answer(cb)
    _, _, idx_str, page_str = cb.data.split(":")
    idx, page = int(idx_str), int(page_str)

    data = await state.get_data()
    raw = list(data.get("cart", []))

    decoded = []
    for key in raw:
        try:
            subj, sec = key.split(_SEP, 1)
        except Exception:
            continue
        decoded.append((subj, sec))

    decoded.sort(key=lambda x: (x[0].lower(), x[1].lower()))

    if 0 <= idx < len(decoded):
        subj, sec = decoded[idx]
        key = f"{subj}{_SEP}{sec}"

        raw_set = set(raw)
        if key in raw_set:
            raw_set.remove(key)
            await state.update_data(cart=list(raw_set))

    await render_paysec_cart(cb.message, cb.from_user.id, api_client, state, page=page)


@router.callback_query(F.data == "paysec:cartclear")
async def cb_paysec_cartclear(cb: CallbackQuery, api_client: APIGatewayClient, state: FSMContext):
    await cb.answer()
    await state.update_data(cart=[])
    await render_paysec_cart(cb.message, cb.from_user.id, api_client, state, page=0)
