from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from handlers.start import Start
from keyboards.catalog import keyboard_catalog, keyboard_catalog_student, keyboard_catalog_student_pass, keyboard_catalog_student_pass_confirm
from keyboards.start import keyboard_teacher_start
from utils.catalog import add_student
from utils.users import Student, Teacher
from utils.template import DinamicKeyboard

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

@router_catalog.message(F.text == 'Список заданий')
async def catalog4(message: Message):
    try:
        await message.answer('Выберите', reply_markup=keyboard_catalog_student.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog4: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'view_active_tasks')
async def catalog5(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if student.homework_active:
            await callback.message.answer(f"Ваши активные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'ts_{callback.from_user.id}').generate_keyboard())
        else:
            await callback.message.answer("У вас нет активных заданий.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog5: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:15] == 'callback_datats')
async def catalog6(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        task_id = int(callback.data.split('_')[3])
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if selected_task:
            teacher = Teacher()
            teacher.get_statistics(selected_task[0]['id_teacher'])
            if selected_task[0]['file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
            await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}", parse_mode=keyboard_catalog_student_pass.markup)
        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog6: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

