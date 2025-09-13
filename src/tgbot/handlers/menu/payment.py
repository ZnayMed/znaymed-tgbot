import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.payment_kb import kb_pay_root, kb_payment_link
from tgbot.utils.edit_or_respawn import edit_or_respawn

router = Router(name="menu.payment")
log = logging.getLogger(__name__)

PER_PAGE_PAY = 8


def _format_money(kopeck: int, currency: str) -> str:
    rub = max(0, int(kopeck)) // 100
    kop = max(0, int(kopeck)) % 100
    curr = currency or "RUB"
    curr_symbol = "₽" if curr.upper() in {"RUB", "RUR", "RUBLE", "RU"} or curr == "₽" else curr
    return f"{rub}.{kop:02d} {curr_symbol}" if kop != 0 else f"{rub} {curr_symbol}"


def _discount_suffix(subtotal_kopeck: int, discounted_kopeck: int) -> str:
    if subtotal_kopeck and discounted_kopeck < subtotal_kopeck:
        pct = int(round((subtotal_kopeck - discounted_kopeck) * 100 / subtotal_kopeck))
        return f" (−{pct}%)"
    return ""


async def render_pay_root(msg, user_id: int, api: APIGatewayClient, page: int = 0):
    try:
        pricing = await api.get_all_subjects_pricing(user_id)
    except Exception:
        return await edit_or_respawn(msg, user_id, t("pay_error"), kb_pay_root([], page=0))

    subjects_raw = list(pricing.get("subjects") or [])
    currency = str(pricing.get("currency") or "RUB")

    subjects = [s.get("subject", "") for s in subjects_raw if s.get("subject")]
    subject_price_map: dict[str, str] = {}
    payable_subjects: set[str] = set()

    for s in subjects_raw:
        subject = s.get("subject", "")
        missing = int(s.get("missing_count", 0) or 0)
        subtotal = int(s.get("subtotal_kopeck", 0) or 0)
        discounted = int(s.get("discounted_kopeck", 0) or 0)
        if subject and missing > 0 and discounted > 0:
            subject_price_map[subject] = _format_money(discounted, currency) + _discount_suffix(subtotal, discounted)
            payable_subjects.add(subject)

    total = pricing.get("total") or {}
    total_missing = int(total.get("missing_count", 0) or 0)
    total_subtotal = int(total.get("subtotal_kopeck", 0) or 0)
    total_discounted = int(total.get("discounted_kopeck", 0) or 0)
    total_rule = str(total.get("applied_rule") or "")

    if total_missing <= 0 or total_discounted <= 0:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="◀️ В меню", callback_data="menu:root"))
        return await edit_or_respawn(msg, user_id, t("pay_all_bought"), b.as_markup())

    all_btn_text = _format_money(total_discounted, currency) + _discount_suffix(total_subtotal, total_discounted)

    return await edit_or_respawn(
        msg,
        user_id,
        t("pay_title"),
        kb_pay_root(
            subjects,
            page=page,
            per_page=PER_PAGE_PAY,
            row_width=1,
            all_btn_text=f"Все разделы — {all_btn_text}",
            subject_price_map=subject_price_map,
            payable_subjects=payable_subjects,
        ),
    )


async def render_payment_screen(
        msg,
        user_id: int,
        *,
        payment_id: str,
        payment_url: str,
        total_kopeck: int,
        currency: str,
        missing_sections: list[str] | None = None,
        show_amount=False
):
    lines = [
        t("payment_screen_title"),
    ]

    if show_amount and (total_kopeck or 0) > 0:
        lines.append("")
        amount_text = _format_money(total_kopeck, currency)
        # lines.append(t("payment_screen_amount").format(amount=amount_text))
    if missing_sections is not None:
        lines.append(t("payment_screen_positions").format(n=len(missing_sections)))
        [lines.append(section) for section in missing_sections]
    lines.append("")
    lines.append(t("payment_screen_cta"))

    text = "\n".join(lines)

    return await edit_or_respawn(
        msg,
        user_id,
        text,
        kb_payment_link(payment_url),
    )


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
async def cb_pay_buy_all(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    try:
        pricing = await api_client.get_all_subjects_pricing(cb.from_user.id)
        subjects = [s.get("subject") for s in (pricing.get("subjects") or []) if (s.get("missing_count") or 0) > 0]
    except Exception as e:
        log.exception("get_all_subjects_pricing failed: %s", e)
        await cb.answer(t("api_error"), show_alert=True)
        return

    if not subjects:
        await cb.answer(t("pay_nothing_to_buy"), show_alert=True)
        return

    try:
        resp = await api_client.create_payment_subjects(cb.from_user.id, subjects)
    except Exception as e:
        log.exception("create_payment_missing_sections failed: %s", e)
        await cb.answer(t("pay_create_failed"), show_alert=True)
        return

    sections = list(resp.get("sections") or [])
    if not sections:
        await cb.answer(t("pay_nothing_to_buy"), show_alert=True)
        return

    try:
        priced = await api_client.get_sections_total(cb.from_user.id, sections)
        total_kopeck = int(priced.get("total_kopeck", 0) or 0)
        currency = str(priced.get("currency") or "")
    except Exception as e:
        log.exception("get_sections_total failed: %s", e)
        total_kopeck, currency = 0, ""

    payment_id = str(resp.get("payment_id", ""))
    payment_url = str(resp.get("payment_url", ""))

    if not payment_url:
        await cb.answer(t("pay_missing_url"), show_alert=True)
        return

    await render_payment_screen(
        cb.message,
        cb.from_user.id,
        payment_id=payment_id,
        payment_url=payment_url,
        total_kopeck=total_kopeck,
        currency=currency,
        missing_sections=sections,
        show_amount=True,
    )


@router.callback_query(F.data.startswith("pay:subject:"))
async def cb_pay_buy_subject(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    try:
        idx = int(cb.data.split(":")[-1])
    except Exception:
        await cb.answer(t("api_error"), show_alert=True)
        return

    try:
        pricing = await api_client.get_all_subjects_pricing(cb.from_user.id)
        subjects = [s.get("subject") for s in (pricing.get("subjects") or []) if s.get("subject")]
    except Exception as e:
        log.exception("get_all_subjects_pricing failed: %s", e)
        await cb.answer(t("api_error"), show_alert=True)
        return

    if not (0 <= idx < len(subjects)):
        await render_pay_root(cb.message, cb.from_user.id, api_client, page=0)
        return

    subject = subjects[idx]

    try:
        resp = await api_client.create_payment_subjects(cb.from_user.id, [subject])
    except Exception as e:
        log.exception("create_payment_missing_sections failed: %s", e)
        await cb.answer(t("pay_create_failed"), show_alert=True)
        return

    sections = list(resp.get("sections") or [])
    if not sections:
        await cb.answer(t("pay_nothing_to_buy"), show_alert=True)
        return

    try:
        priced = await api_client.get_sections_total(cb.from_user.id, sections)
        total_kopeck = int(priced.get("total_kopeck", 0) or 0)
        currency = str(priced.get("currency") or "")
    except Exception as e:
        log.exception("get_sections_total failed: %s", e)
        total_kopeck, currency = 0, ""

    payment_id = str(resp.get("payment_id", ""))
    payment_url = str(resp.get("payment_url", ""))

    if not payment_url:
        await cb.answer(t("pay_missing_url"), show_alert=True)
        return

    await render_payment_screen(
        cb.message,
        cb.from_user.id,
        payment_id=payment_id,
        payment_url=payment_url,
        total_kopeck=total_kopeck,
        currency=currency,
        missing_sections=sections,
        show_amount=True,
    )
