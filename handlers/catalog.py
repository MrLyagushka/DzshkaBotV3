from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from handlers.start import Start
from keyboards.catalog import keyboard_catalog
from keyboards.start import keyboard_teacher_start
from utils.catalog import add_student
from utils.users import Student

class Catalog(StatesGroup):
    first = State()
    second = State()
    third = State()

router_catalog = Router()

@router_catalog.message(F.text == 'Список учеников')
async def catalog1(message: Message):
    try:
        await message.answer('Выберите действие', reply_markup=keyboard_catalog.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog1: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'add_student')
async def catalog2(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.answer('Введите id ученика для добавления')
        await state.set_state(Catalog.first)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog2: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.message(Catalog.first)
async def catalog3(message: Message, state: FSMContext):
    try:
        if not isinstance(message.text, int):
            await message.answer('❌ID ученика должен быть числом, попробуйте еще раз', reply_markup=keyboard_teacher_start.markup)
        else:
            student_id = int(message.text)
            is_exists = Student()
            is_exists.get_statistics(student_id)
        
            if is_exists.name_student == []:
                await message.answer('❌Ученик с таким ID не найден, попробуйте еще раз', reply_markup=keyboard_teacher_start.markup)
            else:
                add_student(student_id, message.from_user.id)
                student = Student()
                student.get_statistics(student_id)
                await message.answer(f'Ученик {student.name_student} успешно добавлен!')
                await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog3: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')