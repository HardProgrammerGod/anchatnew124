import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, PORT
from handlers import common, location, chat, admin

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота с дефолтным HTML-парсером
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хендлер для UptimeRobot (Keep-Alive)
async def handle_ping(request):
    return web.Response(text="Bot is alive!", status=200)

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"Web server started on port {PORT} for UptimeRobot")

async def main():
    # Регистрация роутеров
    dp.include_routers(
        admin.router,
        common.router,
        location.router,
        chat.router
    )
    
    # Запуск веб-сервера для аптайма
    await start_webserver()
    
    # Пропуск накопившихся апдейтов и старт поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
