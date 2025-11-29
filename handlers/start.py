from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from utils.start import are_you_new_user, add_user_to_db, add_student_to_db, add_teacher_to_db
from utils.filter import is_student, is_teacher
from keyboards.start import keyboard_start, keyboard_student_start, keyboard_teacher_start

router_start = Router()

class Start(StatesGroup):
    first = State()
    second = State()
    third = State()
    fourth = State()

@router_start.message(CommandStart())
async def start1(message: Message, state: FSMContext):
    try:
        if are_you_new_user(message.from_user.id) == 0:
            add_user_to_db(message.from_user.id, message.from_user.username)
            await message.answer('Привет, ты тут впервые, ты учитель или ученик?', reply_markup=keyboard_start.markup)
            await state.set_state(Start.second)
        elif are_you_new_user(message.from_user.id) == 1:
            message.answer('❌Ошибка, обратитесь в поддержку')
        elif are_you_new_user(message.from_user.id) != 0:
            if message.from_user.id in [x['id'] for x in is_teacher()]:
                await message.answer('Привет, хорошего дня', reply_markup=keyboard_teacher_start.markup)
                await state.set_state(Start.first)
            elif message.from_user.id in [x['id'] for x in is_student()]:
                await message.answer('Привет, хорошего дня', reply_markup=keyboard_student_start.markup)
                await state.set_state(Start.first)
    except Exception as e:
        logging.error(f"Ошибка в функции start: {e}")
        message.answer('❌Ошибка, обратитесь в поддержку')

@router_start.message(Start.second)
async def start2(message: Message, state: FSMContext):
    try:
        await state.set_state(Start.third)
        await state.update_data(text=message.text)
        await message.answer('Введите свое имя:')
    except Exception as e:
        logging.error(f"Ошибка в функции start2: {e}")
        message.answer('❌Ошибка, обратитесь в поддержку')

@router_start.message(Start.third)
async def start3(message: Message, state: FSMContext):
    try:
        await state.update_data(name=message.text)
        name = (await state.get_data())['name']
        text = (await state.get_data())['text']
        if text == 'Учитель':
            await message.answer('Привет, хорошего дня!', reply_markup=keyboard_teacher_start.markup)
            add_teacher_to_db(message.from_user.id, message.from_user.username, name)
        elif text == 'Ученик':
            await message.answer('Привет, хорошего дня!', reply_markup=keyboard_student_start.markup)
            add_student_to_db(message.from_user.id, message.from_user.username, name)
        await state.set_state(Start.first)
    except Exception as e:
        logging.error(f"Ошибка в функции start3: {e}")
        message.answer('❌Ошибка, обратитесь в поддержку')