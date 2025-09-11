from __future__ import annotations

import asyncio
import logging
import os

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
from tgbot.middleware.auto_answer import AutoAnswerMiddleware
from tgbot.services.api_client import APIGatewayClient

# === Конфиг из env/настроек ===
BOT_WEB_HOST = os.getenv("BOT_WEB_HOST", "0.0.0.0")
BOT_WEB_PORT = int(os.getenv("BOT_WEB_PORT", "9000"))
BOT_WEBHOOK_PATH = os.getenv("BOT_WEBHOOK_PATH", "/tg/webhook")
BOT_WEBHOOK_BASE = os.getenv("BOT_WEBHOOK_BASE", "https://znaymed.ru").rstrip("/")
BOT_WEBHOOK_SECRET = os.getenv("BOT_WEBHOOK_SECRET")  # обязателен

PUBLIC_WEBHOOK_URL = f"{BOT_WEBHOOK_BASE}{BOT_WEBHOOK_PATH}"

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
        BotCommand(command="change_email", description="Смена почты")
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def on_startup() -> None:
    await set_commands()
    log.info("Bot starting…")


async def on_shutdown() -> None:
    log.info("Bot closing…")
    await bot.session.close()


@dp.shutdown.register
async def _close_api_client():
    await api_client.aclose()
    log.info("API client closed")


def build_app() -> web.Application:
    # middlewares/routers — как в polling-версии
    dp.callback_query.middleware.register(AutoAnswerMiddleware())
    dp.message.middleware.register(APIClientMiddleware(api_client))
    dp.callback_query.middleware.register(APIClientMiddleware(api_client))
    dp.update.outer_middleware(APIClientMiddleware(api_client))
    dp.message.middleware.register(RegistrationGuardMiddleware(api_client))
    for r in all_routers:
        dp.include_router(r)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Хендлер вебхука с проверкой секретного токена из заголовка
    # 'X-Telegram-Bot-Api-Secret-Token'
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=BOT_WEBHOOK_SECRET,
    ).register(app, path=BOT_WEBHOOK_PATH)

    # При старте приложения — ставим вебхук у Telegram
    async def _app_on_startup(_app: web.Application):
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(
            url=PUBLIC_WEBHOOK_URL,
            secret_token=BOT_WEBHOOK_SECRET,
            allowed_updates=["message", "callback_query", "inline_query", "chat_member"],
            drop_pending_updates=True,
        )
        log.info("Webhook set to %s", PUBLIC_WEBHOOK_URL)

    # При остановке — удаляем вебхук (опционально)
    async def _app_on_shutdown(_app: web.Application):
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            pass

    app.on_startup.append(_app_on_startup)
    app.on_shutdown.append(_app_on_shutdown)

    # Привязываем DP к приложению (активирует dp.startup/shutdown)
    setup_application(app, dp, bot=bot)
    return app


async def main() -> None:
    app = build_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host=BOT_WEB_HOST, port=BOT_WEB_PORT)
    await site.start()
    log.info("Webhook server listening on http://%s:%s%s", BOT_WEB_HOST, BOT_WEB_PORT, BOT_WEBHOOK_PATH)

    # Блокируемся, пока не SIGTERM
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger(__name__)
    asyncio.run(main())
