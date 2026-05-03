from aiogram import F, Router
from aiogram.types import Message
import logging

from keyboards.catalog_main_menu import keyboard_catalog_main_menu

router_main_keyboard = Router()

@router_main_keyboard.message(F.text == 'Список учеников')
async def catalog1(message: Message):
    try:
        await message.answer('Выберите действие', reply_markup=keyboard_catalog_main_menu.markup)
        
    except Exception as e:
        logging.error(f"Ошибка в функции catalog1: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')