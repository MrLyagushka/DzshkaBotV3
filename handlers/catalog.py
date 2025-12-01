from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

from handlers.start import Start
from keyboards.catalog import keyboard_catalog, keyboard_catalog_student, keyboard_catalog_student_pass, keyboard_catalog_student_pass_confirm
from keyboards.start import keyboard_teacher_start, keyboard_student_start
from utils.catalog import add_student, save_answer_task, get_id_teacher
from utils.users import Student, Teacher
from utils.template import DinamicKeyboard

class Catalog(StatesGroup):
    first = State()
    second = State()
    third = State()

router_catalog = Router()

async def special_function(message: Message, state: FSMContext):
    task_id = (await state.get_data())['selected_task_id']
    student = Student()
    student.get_students_tasks(message.from_user.id)
    selected_task = [task for task in student.homework_active if task['id'] == task_id]
    if selected_task:
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await message.answer_document(document=document_to_send, caption='Файл к заданию')
        await message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}", reply_markup=keyboard_catalog_student_pass.markup)
    else:
        await message.answer("Задание не найдено.")

async def special_function_callback(callback: CallbackQuery, state: FSMContext):
    task_id = (await state.get_data())['selected_task_id']
    student = Student()
    student.get_students_tasks(callback.from_user.id)
    selected_task = [task for task in student.homework_active if task['id'] == task_id]
    if selected_task:
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}", reply_markup=keyboard_catalog_student_pass.markup)
    else:
        await callback.message.answer("Задание не найдено.")

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
        await state.update_data(selected_task_id=task_id)
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if selected_task:
            teacher = Teacher()
            teacher.get_statistics(selected_task[0]['id_teacher'])
            if selected_task[0]['file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
            await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}", reply_markup=keyboard_catalog_student_pass.markup)
            await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)
        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog6: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'add_text_to_task')
async def catalog10(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пришлите текст для добавления к заданию')
        await state.set_state(Catalog.second)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog10: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.message(Catalog.second)
async def catalog11(message: Message, state: FSMContext):
    try:
        await state.update_data(added_text=message.text)
        await message.answer('Текст успешно добавлен к заданию.')
        await special_function(message, state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog11: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'add_file_to_task')
async def catalog12(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пришлите файл для добавления к заданию')
        await state.set_state(Catalog.third)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog12: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.message((F.document | F.photo | F.video | F.audio), Catalog.third)
async def catalog13(message: Message, state: FSMContext, bot: Bot):
    try:
        # 2. Определяем тип и скачиваем файл → получаем bytes
        file_data: bytes | None = None
        file_name: str | None = None
        file_type: str | None = None

        if message.document:
            file = await bot.get_file(message.document.file_id)
            file_data = (await bot.download_file(file.file_path)).read()
            file_name = message.document.file_name
            file_type = "document"
        elif message.photo:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            file_data = (await bot.download_file(file.file_path)).read()
            file_name = "photo.jpg"
            file_type = "photo"
        elif message.video:
            file = await bot.get_file(message.video.file_id)
            file_data = (await bot.download_file(file.file_path)).read()
            file_name = message.video.file_name or "video.mp4"
            file_type = "video"
        elif message.audio:
            file = await bot.get_file(message.audio.file_id)
            file_data = (await bot.download_file(file.file_path)).read()
            file_name = message.audio.file_name or "audio.mp3"
            file_type = "audio"
        else:
            await message.answer("Поддерживаются только: фото, документы, видео, аудио.")
            await special_function(message, state)
        if file_data.__sizeof__() > 10500000:
            await message.answer("Файл слишком большой, максимальный размер файла 10 МБ.")
            await special_function(message, state)
        else:
            await state.update_data(file_name=file_name, file_type=file_type, file_data=file_data)
            await message.answer('Файл прикреплен')
            await special_function(message, state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog13: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'pass_task')
async def catalog7(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Вы уверены, что хотите сдать задание?', reply_markup=keyboard_catalog_student_pass_confirm.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog7: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'confirm_pass_task')
async def catalog8(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.answer()
        if (await state.get_data())['added_text'] == None:
            await callback.message.answer('Прикрепите текст ответа сначала')
            await special_function_callback(callback, state)
        else:
            await callback.message.answer('Задание сдано преподавателю. Ожидайте проверки.', reply_markup=keyboard_student_start.markup)
            save_answer_task(
                id_task=(await state.get_data())['selected_task_id'],
                answer_text=(await state.get_data())['added_text'],
                answer_file_name=(await state.get_data())['file_name'],
                answer_file_type=(await state.get_data())['file_type'],
                answer_file_data=(await state.get_data())['file_data']
            )
            student = Student()
            student.get_statistics(callback.from_user.id)
            await bot.send_message(get_id_teacher((await state.get_data())['selected_task_id']), f"Ученик {student.name_student['name']} сдал задание. Проверьте его.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog8: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'cancel_pass_task')
async def catalog9(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Сдача задания отменена.', reply_markup=keyboard_catalog_student.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog9: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')