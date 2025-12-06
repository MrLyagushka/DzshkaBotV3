from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pytz
import asyncio
import logging

from aiogram import Dispatcher, Bot
from config import BOT_TOKEN, ADMIN_ID
from handlers.start import router_start
from handlers.profile import router_profile
from handlers.homework import router_homework
from handlers.service_handlers import router_service_handlers
from handlers.catalog import router_catalog
from handlers.main_keyboard import router_main_keyboard
from handlers.tutorial import router_tutorial

from utils.reminders import send_reminder_3d, send_reminder_1d
from utils.backup import backup_scheduler, create_backup

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))

async def main():
    # Подключаем роутеры
    dp.include_routers(
        router_start,
        router_tutorial,
        router_main_keyboard,
        router_profile,
        router_homework,
        router_catalog,
        router_service_handlers
    )

    # Запускаем планировщик бекапа в фоне
    asyncio.create_task(backup_scheduler(bot))
    asyncio.create_task(create_backup(bot))

    scheduler.add_job(
        send_reminder_3d,
        "cron",
        hour=9, minute=0,
        args=[bot],
        id=f"hw_reminder_3d"
    )
    scheduler.add_job(
        send_reminder_1d,
        "cron",
        hour=9, minute=0,
        args=[bot],
        id=f"hw_reminder_1d"
    )

    scheduler.start()
    
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
