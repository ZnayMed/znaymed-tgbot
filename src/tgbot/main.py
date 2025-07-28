import asyncio
from aiogram import Bot, Dispatcher

async def main():
    bot = Bot("TELEGRAM_TOKEN")
    dp = Dispatcher()
    # настройте хендлеры …
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
