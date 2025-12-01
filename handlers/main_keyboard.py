from aiogram import F, Router
from aiogram.types import Message
import logging

from keyboards.catalog import keyboard_catalog

router_main_keyboard = Router()

@router_main_keyboard.message(F.text == 'Список учеников')
async def catalog1(message: Message):
    try:
        await message.answer('Выберите действие', reply_markup=keyboard_catalog.markup)
        
    except Exception as e:
        logging.error(f"Ошибка в функции catalog1: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')