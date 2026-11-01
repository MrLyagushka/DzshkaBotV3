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
        # §5: один запрос are_you_new_user вместо тройного (было: ==0, ==1, !=0)
        new_user = are_you_new_user(message.from_user.id)
        if new_user == 0:
            add_user_to_db(message.from_user.id, message.from_user.username)
            await message.answer('Привет, ты тут впервые, ты учитель или ученик?', reply_markup=keyboard_start.markup)
            await state.set_state(Start.second)
        elif new_user == 1:
            await message.answer('❌Ошибка, обратитесь в поддержку')
        else:
            # §5: точечные проверки роли (SELECT 1 ... WHERE id = ?) вместо
            # загрузки всей таблицы; None — сбой БД, не «не состоит»
            if is_teacher(message.from_user.id):
                await message.answer('Привет, хорошего дня', reply_markup=keyboard_teacher_start.markup)
                await state.set_state(Start.first)
            elif is_student(message.from_user.id):
                await message.answer('Привет, хорошего дня', reply_markup=keyboard_student_start.markup)
                await state.set_state(Start.first)
            else:
                await message.answer('❌Ошибка, обратитесь в поддержку')
    except Exception as e:
        logging.error(f"Ошибка в функции start: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_start.message(Start.second)
async def start2(message: Message, state: FSMContext):
    try:
        await state.set_state(Start.third)
        await state.update_data(text=message.text)
        await message.answer('Введите свое имя:')
    except Exception as e:
        logging.error(f"Ошибка в функции start2: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

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
        await message.answer('❌Ошибка, обратитесь в поддержку')