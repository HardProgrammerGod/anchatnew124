import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, PORT
from handlers import common, location, chat, admin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

# Инициализация бота и легковесного хранилища состояний (FSM) в ОЗУ
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ВЕБ-СЕРВЕР ДЛЯ KEEP-ALIVE (UPTIMEROBOT) ---

async def handle_ping(request):
    """Возвращает 200 OK для UptimeRobot, предотвращая засыпание контейнера Render"""
    return web.Response(text="Bot is alive!", status=200)

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    logging.info(f"Web server successfully started on port {PORT}")
    # Возвращаем runner, чтобы удерживать его в глобальном event loop и избегать сборки мусора
    return runner

# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ---

async def main():
    # Строгий порядок регистрации роутеров:
    # 1. Admin — перехватывает команды управления и админские FSM-состояния рассылки.
    # 2. Common — стартовые команды, проверка подписки, профиль и рефералка.
    # 3. Location — цепочки инлайн-кнопок выбора стран.
    # 4. Chat — ядро анонимного чата (обрабатывает весь свободный текст в последнюю очередь).
    dp.include_routers(
        admin.router,
        common.router,
        location.router,
        chat.router
    )
    
    # Запускаем веб-сервер и сохраняем ссылку на runner в локальную переменную
    _web_runner = await start_webserver()
    
    # Очищаем очередь старых сообщений, чтобы бот не спамил юзерам после перезапуска/деплоя
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("Starting anonymous chat bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        # Корректное закрытие ресурсов при остановке приложения
        await bot.session.close()
        await _web_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by signal!")
