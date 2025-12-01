import asyncio
import logging

# Импорт библиотек
from aiogram import Dispatcher, Bot
# Импорт констант
from config import BOT_TOKEN
from handlers.start import router_start
from handlers.profile import router_profile
from handlers.homework import router_homework
from handlers.service_handlers import router_service_handlers
from handlers.catalog import router_catalog
from handlers.main_keyboard import router_main_keyboard

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():
    dp.include_routers(router_start, router_main_keyboard, router_profile, router_homework, router_catalog, router_service_handlers)
    await dp.start_polling(bot)


if __name__ == '__main__':
    file_log = logging.FileHandler('logging.log')
    console_out = logging.StreamHandler()
    logging.basicConfig(level=logging.INFO, handlers=(file_log, console_out))
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
        logging.info('Программа завершила работу по Ctrl + C')
    except Exception as exc:
        logging.info(f'{exc}')
