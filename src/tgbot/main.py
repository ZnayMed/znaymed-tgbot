from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin

import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from tgbot.config import settings
from tgbot.handlers import all_routers
from tgbot.middleware.api_client import APIClientMiddleware
from tgbot.middleware.registration_guard import RegistrationGuardMiddleware
from tgbot.services.api_client import APIGatewayClient


log = logging.getLogger(__name__)
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode="HTML"),
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

api_client = APIGatewayClient(
    base_url=str(settings.api_gateway_url),
    timeout=10.0,
)


async def set_commands():
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="info", description="Информация"),
        BotCommand(command="menu", description="Главное меню"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def on_startup() -> None:
    await set_commands()
    webhook_url = urljoin(str(settings.webhook_base), str(settings.webhook_path))
    await bot.set_webhook(
        url=webhook_url,
        secret_token=str(settings.webhook_secret),
        drop_pending_updates=True,
    )
    log.info("Webhook set to %s", webhook_url)
    log.info("Bot starting…")


async def on_shutdown() -> None:
    log.info("Bot closing…")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        log.warning("delete_webhook failed: %s", e)
    await bot.session.close()


@dp.shutdown.register
async def _close_api_client():
    await api_client.aclose()
    log.info("API client closed")


async def main() -> None:
    # middlewares
    dp.message.middleware.register(APIClientMiddleware(api_client))
    dp.callback_query.middleware.register(APIClientMiddleware(api_client))
    dp.message.middleware.register(RegistrationGuardMiddleware(api_client))

    # routers
    for r in all_routers:
        dp.include_router(r)

    # lifecycle
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # --- AIOHTTP app for webhook ---
    app = web.Application()

    # optional healthcheck
    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/healthz", health)

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=str(settings.webhook_secret),
    )
    app.router.add_post(str(settings.webhook_path), handler.handle)

    setup_application(app, dp, bot=bot)

    host = str(getattr(settings, "web_host", "0.0.0.0"))
    port = int(getattr(settings, "web_port", 8081))
    log.info("Starting aiohttp on %s:%s", host, port)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()

    # держим процесс живым
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    try:
        asyncio.run(main())
    except httpx.HTTPError as exc:
        log.exception("Gateway connection error: %s", exc)
