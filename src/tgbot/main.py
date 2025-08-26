from __future__ import annotations

import asyncio
import logging

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from tgbot.config import settings
from tgbot.handlers import all_routers
from tgbot.middleware.api_client import APIClientMiddleware
from tgbot.middleware.registration_guard import RegistrationGuardMiddleware
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
    commands = [BotCommand(command='start', description='Старт'),
                BotCommand(command='info', description='Информация о ЗнайMed'),
                BotCommand(command='menu', description='Главное меню')]
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


async def main() -> None:
    dp.message.middleware.register(APIClientMiddleware(api_client))
    dp.callback_query.middleware.register(APIClientMiddleware(api_client))
    dp.message.middleware.register(RegistrationGuardMiddleware(api_client))

    for r in all_routers:
        dp.include_router(r)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    except httpx.HTTPError as exc:
        log.exception("Gateway connection error: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    log = logging.getLogger(__name__)

    asyncio.run(main())
