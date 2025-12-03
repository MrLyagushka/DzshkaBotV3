# utils/backup.py
import os
import zipfile
from datetime import datetime
import aioschedule
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile  # ← добавлен импорт
from config import ADMIN_ID

DB_PATH = "./db"
BACKUP_DIR = "./backups"


async def create_backup(bot: Bot):
    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    zip_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")

    db_files = [
        os.path.join(DB_PATH, "task.db"),
        os.path.join(DB_PATH, "users.db")
    ]

    existing_files = [f for f in db_files if os.path.exists(f)]
    if not existing_files:
        await bot.send_message(ADMIN_ID, "❌ Нет файлов БД для бекапа.")
        return

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in existing_files:
                zipf.write(file_path, arcname=os.path.basename(file_path))
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка архивации: {e}")
        return

    try:
        # ✅ Правильная отправка файла в aiogram 3+
        await bot.send_document(
            ADMIN_ID,
            document=FSInputFile(zip_path),
            caption=f"✅ Ежедневный бекап от {timestamp}"
        )
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка отправки: {e}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


async def backup_scheduler(bot: Bot):
    aioschedule.every().day.at("02:00").do(lambda: asyncio.create_task(create_backup(bot)))
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)