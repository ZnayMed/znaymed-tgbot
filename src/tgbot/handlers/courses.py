import logging

import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from tgbot.lexicon import t
from tgbot.services.api_client import APIGatewayClient

log = logging.getLogger(__name__)
router = Router()


@router.message(Command("courses"))
async def list_courses(msg: Message, api_client: APIGatewayClient):
    try:
        courses = await api_client.request_json("GET", "/v1/courses")
    except httpx.HTTPError:
        log.exception("Cannot fetch course list")
        await msg.answer(t("api_error"))
        return

    if not courses:
        await msg.answer("Пока нет доступных курсов.")
        return

    lines = [
        f"📚 <b>{c['title']}</b> — <code>{c['id']}</code>" for c in courses
    ]
    lines.append("\nЧтобы купить курс, отправьте /buy <id>")
    await msg.answer("\n".join(lines))


@router.message(Command("buy"))
async def buy(msg: Message, api_client: APIGatewayClient):
    parts = msg.text.split(maxsplit=1)
    if len(parts) != 2:
        await msg.answer("Использование: /buy <id курса>")
        return
    course_id = parts[1]
    try:
        payload = await api_client.request_json(
            "POST", f"/v1/courses/{course_id}/purchase"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await msg.answer("Курс не найден.")
        elif e.response.status_code == 409:
            await msg.answer("Вы уже приобрели этот курс.")
        else:
            log.exception("Purchase failed")
            await msg.answer(t("api_error"))
        return
    except httpx.HTTPError:
        log.exception("Gateway unreachable on purchase")
        await msg.answer(t("api_error"))
        return

    await msg.answer(f"Перейдите для оплаты: {payload.get('payment_url')}")
