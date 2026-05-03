from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
import asyncio
from aiogram_calendar import SimpleCalendarCallback, SimpleCalendar, simple_calendar


from handlers.start import Start
from keyboards.catalog import keyboard_catalog, keyboard_catalog_teacher_check, keyboard_catalog_teacher_pass_confirm, keyboard_choice_marks, keyboard_catalog_student, keyboard_catalog_teacher, keyboard_catalog_student_pass, keyboard_catalog_student_pass_confirm, keyboard_catalog_teacher_check_passed_task
from keyboards.start import keyboard_teacher_start, keyboard_student_start
from keyboards.homework import keyboard_time_selection
from utils.catalog import add_student, save_answer_task, get_id_teacher, set_pass, set_marks, update_deadline, return_goback, get_date, get_is_active
from utils.users import Student, Teacher
from utils.template import DinamicKeyboard
from utils.images_to_pdf import process_album_after_timeout

router_catalog_tasks_list = Router()

class CatalogTasksList(StatesGroup):
    view_active_tasks_student = State()
    view_passed_tasks_student = State()
    view_active_tasks_teacher = State()
    view_passed_tasks_teacher = State()
    view_check_tasks_student = State()
    view_check_tasks_teacher = State()

@router_catalog_tasks_list.callback_query(F.data == 'view_active_tasks_student')
async def catalog5(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 1]:
            await callback.message.answer(f"Ваши активные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsa_{callback.from_user.id}').generate_keyboard())
            await state.set_state(CatalogTasksList.view_active_tasks_student)
        else:
            await callback.message.answer("У вас нет активных заданий")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog5: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')



@router_catalog_tasks_list.callback_query(F.data == 'view_passed_tasks_student')
async def catalog14(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 0]:
            await callback.message.answer(f"Ваши завершенные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsd_{callback.from_user.id}').generate_keyboard())
            await state.set_state(CatalogTasksList.fifth)

        else:
            await callback.message.answer("У вас нет завершенных заданий")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog14: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_active_tasks_teacher')
async def catalog18(callback: CallbackQuery, state: FSMContext):
    try:
        id_student = (await state.get_data())['id_student']
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 1]:
            await callback.message.answer(f"Активные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsa_{id_student}').generate_keyboard())
            await state.set_state(CatalogTasksList.sixth)
        else:
            await callback.message.answer("Нет активных заданий.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog18: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_passed_tasks_teacher')
async def catalog20(callback: CallbackQuery, state: FSMContext):
    try:
        id_student = (await state.get_data())['id_student']
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 0]:
            await callback.message.answer(f"Завершенные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsd_{id_student}').generate_keyboard())
            await state.set_state(CatalogTasksList.sixth)
        else:
            await callback.message.answer("Нет завершенных заданий.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog20: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_check_tasks_student')
async def catalog28(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == -1]:
            await callback.message.answer(f"Задания на проверке", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsp_{callback.from_user.id}').generate_keyboard())
            await state.set_state(CatalogTasksList.fifth)
        else:
            await callback.message.answer("У вас нет заданий на проверке")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog28: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_check_tasks_teacher')
async def catalog30(callback: CallbackQuery, state: FSMContext):
    try:
        id_student = (await state.get_data())['id_student']
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == -1]:
            await callback.message.answer(f"Задания на проверке", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsp_{id_student}').generate_keyboard())
            await state.set_state(CatalogTasksList.sixth)
        else:
            await callback.message.answer("Нет заданий на проверке.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog30: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')