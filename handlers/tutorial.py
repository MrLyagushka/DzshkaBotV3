from aiogram import F, Router
from aiogram.types import Message
from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_TASK
from keyboards.start import keyboard_student_start, keyboard_teacher_start
from utils.filter import is_student, is_teacher

router_tutorial = Router()

@router_tutorial.message(F.text == 'Инструкция')
async def tutorial(message: Message):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT text FROM tutorial")
        if message.from_user.id in [x['id'] for x in is_teacher()]:
            await message.answer(cursor.fetchone()['text'], reply_markup=keyboard_teacher_start.markup)
        elif message.from_user.id in [x['id'] for x in is_student()]:
            await message.answer(cursor.fetchone()['text'], reply_markup=keyboard_student_start.markup)
    except Exception as e:
        logging.error(f'Ошибка в функции tutorial: {e}')
        await message.answer('❌Ошибка, обратитесь в поддержку')
