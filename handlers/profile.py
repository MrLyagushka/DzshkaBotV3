from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from handlers.start import Start
from utils.profile import get_user_profile, reset_name, reset_registration
from utils.filter import is_student, is_teacher
from keyboards.start import keyboard_student_start, keyboard_teacher_start
from keyboards.profile import keyboard_profile_student, keyboard_profile_teacher

class Profile(StatesGroup):
    first = State()
    second = State()
    third = State()

router_profile = Router()

@router_profile.message(F.text == 'Профиль')
async def profile1(message: Message, state: FSMContext):
    try:
        information = get_user_profile(message.from_user.id)
        if message.from_user.id in [x['id'] for x in is_teacher()]:
            await message.answer(f"Привет, {information['teacher']['name']}", reply_markup=keyboard_profile_teacher.markup)
        elif message.from_user.id in [x['id'] for x in is_student()]:
            await message.answer(f"Привет, {information['student']['name']}\nТвой id: {information['student']['id']}", reply_markup=keyboard_profile_student.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции profile1: {e}")
        message.answer('❌Ошибка, обратитесь в поддержку')

@router_profile.callback_query(F.data == 'reset_name')
async def profile2(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.answer('Введите новое имя:')
        await callback.answer()
        await state.set_state(Profile.first)
    except Exception as e:
        logging.error(f"Ошибка в функции profile2: {e}")
        callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_profile.message(Profile.first)
async def profile3(message: Message, state: FSMContext):
    try:
        reset_name(message.from_user.id, message.text)
        information = get_user_profile(message.from_user.id)
        if message.from_user.id in [x['id'] for x in is_teacher()]:
            await message.answer(f"Имя успешно изменено на {information['teacher']['name']}", reply_markup=keyboard_teacher_start.markup)
        elif message.from_user.id in [x['id'] for x in is_student()]:
            await message.answer(f"Имя успешно изменено на {information['student']['name']}", reply_markup=keyboard_student_start.markup)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции profile3: {e}")
        message.answer('❌Ошибка, обратитесь в поддержку')

@router_profile.callback_query(F.data == 'reset_registration')
async def profile4(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        reset_registration(callback.from_user.id)
        print(callback.from_user.id)
        await callback.message.answer('Регистрация успешно сброшена. Чтобы зарегистрироваться заново, нажмите /start')
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции profile4: {e}")
        callback.message.answer('❌Ошибка, обратитесь в поддержку')