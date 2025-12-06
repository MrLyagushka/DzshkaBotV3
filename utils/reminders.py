# utils/reminders.py
from datetime import date, timedelta
import pytz
from aiogram import Bot
import logging

from utils.homework import get_task

MOSCOW_TZ = pytz.timezone("Europe/Moscow")


async def send_reminder_3d(bot: Bot):
    """Напоминание за 3 дня до дедлайна"""
    await _send_reminder(bot, days_before=3, message_suffix="через 3 дня")


async def send_reminder_1d(bot: Bot):
    """Напоминание за 1 день до дедлайна"""
    await _send_reminder(bot, days_before=1, message_suffix="завтра")


async def _send_reminder(bot: Bot, days_before: int, message_suffix: str):
    today = date.today()  # локальная дата, если сервер в нужном TZ
    
    target_deadline = today + timedelta(days=days_before)

    try:
        homework_list = await get_task()
        for hw in homework_list:
            try:
                if str(target_deadline) == (hw['deadline']).split( )[0]:
                    await bot.send_message(
                        chat_id=hw["id_student"],
                        text=(
                            f"🔔 <b>Напоминание о домашнем задании</b>\n\n"
                            f"Дедлайн по заданию на {hw['deadline']}» наступает {message_suffix}!\n"
                            f"Дата сдачи: <code>{target_deadline.strftime('%d.%m.%Y')}</code>"
                        ),
                        parse_mode="HTML"
                    )
            except Exception as e:
                logging.error(f"Не удалось отправить напоминание в чат {hw['id_student']}: {e}")
    except Exception as db_err:
        logging.error(f"Ошибка при получении ДЗ из БД: {db_err}")