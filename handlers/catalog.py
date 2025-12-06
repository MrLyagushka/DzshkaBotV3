from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging
import asyncio

from handlers.start import Start
from keyboards.catalog import keyboard_catalog, keyboard_catalog_teacher_check, keyboard_catalog_teacher_pass_confirm, keyboard_choice_marks, keyboard_catalog_student, keyboard_catalog_teacher, keyboard_catalog_student_pass, keyboard_catalog_student_pass_confirm
from keyboards.start import keyboard_teacher_start, keyboard_student_start
from utils.catalog import add_student, save_answer_task, get_id_teacher, set_pass, set_marks
from utils.users import Student, Teacher
from utils.template import DinamicKeyboard
from utils.images_to_pdf import process_album_after_timeout

class Catalog(StatesGroup):
    first = State()
    second = State()
    third = State()
    fourth = State()
    fifth = State()
    sixth = State()
    seventh = State()

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

@router_catalog.callback_query(F.data == 'add_student')
async def catalog2(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Введите id ученика для добавления')
        await state.set_state(Catalog.first)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog2: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.message(Catalog.first)
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
        if [x for x in student.homework_active if x['is_active'] == 1]:
            await callback.message.answer(f"Ваши активные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsa_{callback.from_user.id}').generate_keyboard())
            await state.set_state(Catalog.fifth)
        else:
            await callback.message.answer("У вас нет активных заданий")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog5: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:16] == 'callback_datatsa', Catalog.fifth)
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
async def catalog7(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пришлите текст для добавления к заданию')
        await state.set_state(Catalog.second)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog7: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.message(Catalog.second)
async def catalog8(message: Message, state: FSMContext):
    try:
        await state.update_data(added_text=message.text)
        await message.answer('Текст успешно добавлен к заданию.')
        await special_function(message, state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog8: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'add_file_to_task')
async def catalog9(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пришлите файл для добавления к решению/ответу')
        await state.set_state(Catalog.third)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog9: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.message(F.photo, Catalog.third)
async def handle_photo_or_album(message: Message, state: FSMContext, bot):
    try:
        media_group_id = message.media_group_id
        current_state = await state.get_data()

        # === Сценарий 1: это фото из альбома ===
        if media_group_id:
            # Проверяем: уже ли мы в процессе сбора альбома?
            if current_state.get("current_album_id") == media_group_id:
                # Уже собираем этот альбом → просто добавляем фото
                album_photos = current_state.get("album_photos", [])
                album_photos.append(message.photo[-1].file_id)
                await state.update_data(album_photos=album_photos)
                return  # Ничего не отвечаем — ждём окончания таймера

            else:
                # Начинаем новый альбом
                await state.update_data(
                    current_album_id=media_group_id,
                    album_photos=[message.photo[-1].file_id],
                    waiting_for_album=True
                )

                # Запускаем фоновую задачу на обработку через таймаут
                asyncio.create_task(
                    process_album_after_timeout(
                        message=message,
                        state=state,
                        bot=bot,
                        chat_id=message.chat.id,
                        expected_media_group_id=media_group_id,
                        Homework=Catalog
                    )
                )
                # Ничего не отвечаем сразу — пользователь увидит сообщение позже
                return

        # === Сценарий 2: одиночное фото ===
        else:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            file_data = await bot.download_file(file.file_path)
            file_bytes = file_data.read()

            await state.update_data(
                file_name="photo.jpg",
                file_type="photo",
                file_data=file_bytes
            )
            await message.answer("Фото прикреплено")
            await special_function(message, state)


    except Exception as e:
        logging.error(f"Ошибка в handle_photo_or_album: {e}")
        await message.answer("❌ Ошибка при обработке фото")
        await special_function(message, state)


@router_catalog.message((F.document | F.photo | F.video | F.audio), Catalog.third)
async def catalog10(message: Message, state: FSMContext, bot: Bot):
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
        logging.error(f"Ошибка в функции catalog10: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'pass_task')
async def catalog11(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Вы уверены, что хотите сдать задание?', reply_markup=keyboard_catalog_student_pass_confirm.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog11: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'confirm_pass_task')
async def catalog12(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
            student.get_students_tasks(callback.from_user.id)
            date = [x for x in student.homework_active if x['id'] == (await state.get_data())['selected_task_id']]
            date = date[0]['deadline']
            await bot.send_message(get_id_teacher((await state.get_data())['selected_task_id']), f"Ученик {student.name_student['name']} сдал(а) задание, заданное на {date}. Проверьте его.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog12: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'cancel_pass_task')
async def catalog13(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Сдача задания отменена.', reply_markup=keyboard_catalog_student.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog13: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'view_passed_tasks')
async def catalog14(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 0]:
            await callback.message.answer(f"Ваши завершенные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsd_{callback.from_user.id}').generate_keyboard())
            await state.set_state(Catalog.fifth)

        else:
            await callback.message.answer("У вас нет завершенных заданий")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog14: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog.callback_query(F.data[:16] == 'callback_datatsd', Catalog.fifth)
async def catalog15(callback: CallbackQuery, state: FSMContext):
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
            if selected_task[0]['answer_file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
            if selected_task[0]['marks'] != None:
                await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}")
            else:
                await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}")

            await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)
        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog15: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'list_students')
async def catalog16(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        teacher = Teacher()
        teacher.get_statistics(callback.from_user.id)
        if teacher.students_info:
            await callback.message.answer('Выберите ученика', reply_markup=DinamicKeyboard(1,3,'no',0,f'st_{callback.from_user.id}').generate_keyboard())
            await state.set_state(Catalog.fourth)
        else:
            await callback.message.answer('У вас нет учеников. Прикрепите ученика через "Список учеников"->"Добавить ученика"', reply_markup=keyboard_teacher_start.markup)
    
    except Exception as e:
        logging.error(f"Ошибка в функции catalog16: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:16] == 'callback_data_st')
async def catalog17(callback: CallbackQuery, state: FSMContext):
    try:
        await state.update_data(id_student=callback.data.split('_')[4])
        await callback.answer()
        await callback.message.answer('Выберите', reply_markup=keyboard_catalog_teacher.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog17: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'view_active_tasks_student')
async def catalog18(callback: CallbackQuery, state: FSMContext):
    try:
        id_student = (await state.get_data())['id_student']
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 1]:
            await callback.message.answer(f"Активные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsa_{id_student}').generate_keyboard())
            await state.set_state(Catalog.sixth)
        else:
            await callback.message.answer("Нет активных заданий.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog18: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:16] == 'callback_datatsa', Catalog.sixth)
async def catalog19(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        task_id = int(callback.data.split('_')[3])
        id_student = (await state.get_data())['id_student']
        await state.update_data(selected_task_id=task_id)
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if selected_task:
            teacher = Teacher()
            teacher.get_statistics(selected_task[0]['id_teacher'])
            if selected_task[0]['file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
            await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}", reply_markup=keyboard_catalog_teacher_check.markup)
        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog19: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'view_passed_tasks_student')
async def catalog20(callback: CallbackQuery, state: FSMContext):
    try:
        id_student = (await state.get_data())['id_student']
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 0]:
            await callback.message.answer(f"Завершенные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsd_{id_student}').generate_keyboard())
            await state.set_state(Catalog.sixth)
        else:
            await callback.message.answer("Нет завершенных заданий.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog20: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:16] == 'callback_datatsd', Catalog.sixth)
async def catalog21(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        id_student = (await state.get_data())['id_student']
        task_id = int(callback.data.split('_')[3])
        await state.update_data(selected_task_id=task_id)
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if selected_task:
            teacher = Teacher()
            teacher.get_statistics(selected_task[0]['id_teacher'])
            if selected_task[0]['file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
            if selected_task[0]['answer_file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
            if selected_task[0]['marks'] != None:
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}")
            else:
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}")

        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog21: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'set_marks')
async def catalog22(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Выберите оценку', reply_markup=keyboard_choice_marks.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog22: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:4] == 'mark')
async def catalog23(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        set_marks((await state.get_data())['selected_task_id'], callback.data[4])
        await callback.message.answer('Оценка установлена', reply_markup=keyboard_catalog_teacher_check.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog23: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'set_passed')
async def catalog24(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Вы уверены?', reply_markup=keyboard_catalog_teacher_pass_confirm.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog24: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'confirm')
async def catalog25(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.answer()
        data = set_pass((await state.get_data())['selected_task_id'])[0]
        await callback.message.answer('Задание отмечено как завершенное', reply_markup=keyboard_teacher_start.markup)
        await bot.send_message(data['id_student'], f'Вам выставили оценку {data["marks"]} по дз на {data["deadline"]}')
    except Exception as e:
        logging.error(f"Ошибка в функции catalog25: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'cancel')
async def catalog26(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Выберите', reply_markup=keyboard_catalog_teacher_check.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog26: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'view_check_tasks')
async def catalog27(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == -1]:
            await callback.message.answer(f"Задания на проверке", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsp_{callback.from_user.id}').generate_keyboard())
            await state.set_state(Catalog.fifth)
        else:
            await callback.message.answer("У вас нет заданий на проверке")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog27: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog.callback_query(F.data[:16] == 'callback_datatsp', Catalog.fifth)
async def catalog28(callback: CallbackQuery, state: FSMContext):
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
            if selected_task[0]['answer_file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
            if selected_task[0]['marks'] != None:
                await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}")
            else:
                await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}")

            await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)
        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog28: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data == 'view_check_tasks_student')
async def catalog29(callback: CallbackQuery, state: FSMContext):
    try:
        id_student = (await state.get_data())['id_student']
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == -1]:
            await callback.message.answer(f"Задания на проверке", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsp_{id_student}').generate_keyboard())
            await state.set_state(Catalog.sixth)
        else:
            await callback.message.answer("Нет заданий на проверке.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog29: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog.callback_query(F.data[:16] == 'callback_datatsp', Catalog.sixth)
async def catalog30(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        id_student = (await state.get_data())['id_student']
        task_id = int(callback.data.split('_')[3])
        await state.update_data(selected_task_id=task_id)
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if selected_task:
            teacher = Teacher()
            teacher.get_statistics(selected_task[0]['id_teacher'])
            if selected_task[0]['file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
            if selected_task[0]['answer_file_name'] != None:
                document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
                await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
            if selected_task[0]['marks'] != None:
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}", reply_markup=keyboard_catalog_teacher_check.markup)
            else:
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания: {selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}", reply_markup=keyboard_catalog_teacher_check.markup)

        else:
            await callback.message.answer("Задание не найдено.")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog30: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
