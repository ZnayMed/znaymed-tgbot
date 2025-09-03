from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from tgbot.config import settings  # <-- твой Settings
from tgbot.handlers import all_routers
from tgbot.middleware.api_client import APIClientMiddleware
from tgbot.middleware.registration_guard import RegistrationGuardMiddleware
from tgbot.middleware.auto_answer import AutoAnswerMiddleware
from tgbot.services.api_client import APIGatewayClient

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
        BotCommand(command="info", description="Информация о ЗнайMed"),
        BotCommand(command="menu", description="Главное меню"),
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
    dp.callback_query.middleware.register(AutoAnswerMiddleware())
    dp.message.middleware.register(APIClientMiddleware(api_client))
    dp.callback_query.middleware.register(APIClientMiddleware(api_client))
    dp.message.middleware.register(RegistrationGuardMiddleware(api_client))
    for r in all_routers:
        dp.include_router(r)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Проверка секрета: если пусто — не проверяем (локалка/тесты)
    secret_token = settings.webhook_secret or None

    # Регистрируем POST-роут вебхука
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret_token,
    ).register(app, path=settings.webhook_path)

    # (опционально) health-check для удобства
    async def health(_req: web.Request):
        return web.Response(text="ok")

    app.router.add_get("/health", health)

    async def _app_on_startup(_app: web.Application):
        # Чистим и выставляем вебхук на публичный URL
        public_url = f"{settings.webhook_base.rstrip('/')}{settings.webhook_path}"
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(
            url=public_url,
            secret_token=secret_token,  # None — без секрета
            allowed_updates=["message", "callback_query", "inline_query", "chat_member"],
            drop_pending_updates=True,
        )
        log.info("Webhook set to %s", public_url)

    async def _app_on_shutdown(_app: web.Application):
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            pass

    app.on_startup.append(_app_on_startup)
    app.on_shutdown.append(_app_on_shutdown)

    # Активируем dp.startup/shutdown хуки
    setup_application(app, dp, bot=bot)
    return app


async def main() -> None:
    app = build_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.web_host, port=settings.web_port)
    await site.start()
    log.info(
        "Webhook server listening on http://%s:%s%s",
        settings.web_host, settings.web_port, settings.webhook_path,
    )
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger(__name__)
    asyncio.run(main())
