import asyncio
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient
from tgbot.keyboards.payment_kb import kb_pay_root, kb_payment_link
from .utils import edit_or_respawn

router = Router(name="menu.payment")
log = logging.getLogger(__name__)

PER_PAGE_PAY = 8


def _format_money(kopeck: int, currency: str) -> str:
    rub = max(0, int(kopeck)) // 100
    kop = max(0, int(kopeck)) % 100
    curr = currency or "RUB"
    curr_symbol = "₽" if curr.upper() in {"RUB", "RUR", "RUBLE", "RU"} or curr == "₽" else curr
    return f"{rub}.{kop:02d} {curr_symbol}"


async def _fetch_subject_total(api: APIGatewayClient, user_id: int, subject: str, sem: asyncio.Semaphore):
    async with sem:
        try:
            data = await api.get_subject_total(user_id, subject)
            return subject, int(data.get("total_kopeck", 0)), str(data.get("currency", "RUB"))
        except Exception:
            return subject, None, None


async def render_pay_root(msg, user_id: int, api: APIGatewayClient, page: int = 0):
    try:
        subjects = await api.get_subjects()
    except Exception:
        # в случае ошибки всё равно покажем шапку и кнопку "в меню"
        return await edit_or_respawn(msg, user_id, t("pay_error"), kb_pay_root([], page=0))

    # считаем цены для каждого предмета и общий итог
    subject_price_map: dict[str, str] = {}
    payable_subjects: set[str] = set()
    all_total_kopeck = 0
    all_currency = "RUB"

    if subjects:
        sem = asyncio.Semaphore(5)
        tasks = [asyncio.create_task(_fetch_subject_total(api, user_id, s, sem)) for s in subjects]
        results = await asyncio.gather(*tasks)

        for subj, kopeck, curr in results:
            if kopeck is None:
                continue
            all_total_kopeck += kopeck
            all_currency = curr or all_currency
            if kopeck > 0:
                subject_price_map[subj] = _format_money(kopeck, curr or "RUB")
                payable_subjects.add(subj)

    # кнопку "Все предметы" показываем только если есть что покупать
    all_btn_text = (
        f"Все предметы — {_format_money(all_total_kopeck, all_currency)}"
        if all_total_kopeck > 0 else None
    )

    return await edit_or_respawn(
        msg,
        user_id,
        t("pay_title"),
        kb_pay_root(
            subjects,
            page=page,
            per_page=PER_PAGE_PAY,
            row_width=1,
            all_btn_text=all_btn_text,
            subject_price_map=subject_price_map,  # подписи цен
            payable_subjects=payable_subjects,  # показываем только эти предметы
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
    amount_text = _format_money(total_kopeck, currency)

    lines = [
        t("payment_screen_title"),
    ]

    if show_amount and (total_kopeck or 0) > 0:
        amount_text = _format_money(total_kopeck, currency)
        lines.append(t("payment_screen_amount").format(amount=amount_text))
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
        subjects = await api_client.get_subjects()
    except Exception as e:
        log.exception("get_subjects failed: %s", e)
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

    payment_id = str(resp.get("payment_id", ""))
    payment_url = str(resp.get("payment_url", ""))
    status = str(resp.get("status", ""))

    if not payment_url:
        await cb.answer(t("pay_missing_url"), show_alert=True)
        return

    await render_payment_screen(
        cb.message,
        cb.from_user.id,
        payment_id=payment_id,
        payment_url=payment_url,
        total_kopeck=0,  # суммы пока нет
        currency="",  # валюты пока нет
        missing_sections=sections,
        show_amount=False,  # <-- скрываем сумму
    )


@router.callback_query(F.data.startswith("pay:subject:"))
async def cb_pay_buy_subject(cb: CallbackQuery, api_client: APIGatewayClient):
    await cb.answer()
    # индекс предмета — глобальный (как в kb_pay_root)
    try:
        idx = int(cb.data.split(":")[-1])
    except Exception:
        await cb.answer(t("api_error"), show_alert=True)
        return

    try:
        subjects = await api_client.get_subjects()
    except Exception as e:
        log.exception("get_subjects failed: %s", e)
        await cb.answer(t("api_error"), show_alert=True)
        return

    if not (0 <= idx < len(subjects)):
        # список изменился; вернёмся на экран оплаты
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
        total_kopeck=0,
        currency="",
        missing_sections=sections,
        show_amount=False,  # <-- скрываем сумму
    )
