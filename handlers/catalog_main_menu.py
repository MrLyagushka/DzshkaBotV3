from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from keyboards.start import keyboard_teacher_start
from keyboards.catalog_tasks_list import keyboard_catalog_tasks_list_student_pass
from keyboards.catalog_main_menu import keyboard_catalog_main_menu
from utils.users import Teacher, Student
from utils.template import DinamicKeyboard
from utils.catalog import add_student

router_catalog_main_menu = Router()

class CatalogMainMenu(StatesGroup):
    add_student = State()


@router_catalog_main_menu.callback_query(F.data == 'list_students')
async def catalog16(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        teacher = Teacher()
        teacher.get_statistics(callback.from_user.id)
        if teacher.students_info:
            await callback.message.answer('Выберите ученика', reply_markup=DinamicKeyboard(2,3,'no',0,f'st_{callback.from_user.id}').generate_keyboard())

        else:
            await callback.message.answer('У вас нет учеников. Прикрепите ученика через "Список учеников"->"Добавить ученика"', reply_markup=keyboard_teacher_start.markup)
    
    except Exception as e:
        logging.error(f"Ошибка в функции catalog16: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_main_menu.callback_query(F.data == 'add_student')
async def catalog2(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Введите id ученика для добавления')
        await state.set_state(CatalogMainMenu.add_student)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog2: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_main_menu.callback_query(F.data == 'delete_student')
async def catalog2(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пока в разработке')
    except Exception as e:
        logging.error(f"Ошибка в функции catalog2: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_main_menu.message(CatalogMainMenu.add_student)
async def catalog3(message: Message, state: FSMContext):
    try:
        int(message.text)
    except Exception as e:
        await message.answer('❌ID ученика должен быть числом, попробуйте еще раз', reply_markup=keyboard_teacher_start.markup)
        return
    try:
        student_id = int(message.text)
        is_exists = Student()
        is_exists.get_statistics(student_id)
        add_student(student_id, message.from_user.id)
        student = Student()
        student.get_statistics(student_id)
        name = student.name_student['name']
    except Exception as e:
        await message.answer('❌Ученик с таким ID не найден, попробуйте еще раз', reply_markup=keyboard_teacher_start.markup)
        return
    try:
        await message.answer(f'Ученик {name} успешно добавлен!', reply_markup=keyboard_teacher_start.markup)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog3: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_main_menu.message(F.text == 'Список заданий')
async def catalog4(message: Message):
    try:
        await message.answer('Выберите', reply_markup=keyboard_catalog_tasks_list_student_pass.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog4: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

