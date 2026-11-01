from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import logging
import asyncio
from aiogram_calendar import SimpleCalendarCallback, SimpleCalendar, simple_calendar


from handlers.start import Start
from keyboards.catalog_main_menu import keyboard_catalog_main_menu
from keyboards.catalog_tasks_list import keyboard_catalog_tasks_list_teacher_check, keyboard_choice_marks, keyboard_catalog_tasks_list_student, keyboard_catalog_tasks_list_teacher, keyboard_catalog_tasks_list_student_pass, keyboard_catalog_tasks_list_confirm_generic, keyboard_catalog_tasks_list_teacher_check_passed_task, keyboard_catalog_tasks_list_cancel_input, keyboard_time_selection
from keyboards.start import keyboard_teacher_start, keyboard_student_start
from utils.catalog import add_student, save_answer_task, get_id_teacher, set_pass, set_marks, update_deadline, return_goback, get_date, get_is_active
from utils.users import Student, Teacher
from utils.template import DinamicKeyboard
from utils.callbacks import StudentCb, TaskCb, MarkCb, TimeCb
from utils.access import (AccessError, check_ctx_owner, ensure_student_of_teacher,
                          ensure_task_for_student, ensure_task_for_teacher,
                          get_task_row, stale_session)
from utils.images_to_pdf import process_album_after_timeout

router_catalog_tasks_list = Router()

class CatalogTasksList(StatesGroup):
    """Состояния = экраны (см. REFACTORING_GUIDE.md, §2).

    Правило: хендлер колбэка обязан требовать ровно то состояние, которое поставил
    родительский экран. Для динамических списков это <экран>_<роль>:
      tsa -> view_active_tasks_{student|teacher}
      tsd -> view_passed_tasks_{student|teacher}
      tsp -> view_check_tasks_{student|teacher}
    Терминальные шаги (сдал / оценка / подтверждение / дорешка / дедлайн) всегда
    делают state.clear(), чтобы следующие сообщения пользователя не перехватывались
    message-хендлерами чужого экрана (add_text_to_task, _return, add_file_to_task...).
    """
    view_active_tasks_student = State()
    view_passed_tasks_student = State()
    view_active_tasks_teacher = State()
    view_passed_tasks_teacher = State()
    view_check_tasks_student = State()
    view_check_tasks_teacher = State()
    add_text_to_task = State()
    add_file_to_task = State()
    change_deadline = State()
    _return = State()
    # Экраны подтверждения терминальных шагов: кнопки «✅ Подтвердить / ❌ Отменить»
    # матчатся только из своего экрана — живой кнопкой из старого сообщения
    # действие больше не повторить (§2).
    confirm_pass = State()        # ученик подтверждает сдачу задания
    confirm_set_passed = State()  # учитель подтверждает отметку «решено»
    set_mark = State()            # учитель выбрал «Поставить оценку» и ждёт нажатия 2/3/4/5
    add_file_done = State()       # служебный экран: альбом фото собран (см. utils/images_to_pdf)


async def reset_flow(state: FSMContext) -> None:
    """Сброс FSM-экрана + черновиков (см. §2 плана).

    Черновики (added_text/file_*/selected_task_id/id_student/callback_data) живут в том же
    контексте, что и состояние: без их очистки следующий экран может прочитать данные
    предыдущего сообщения/ученика («ошибки доступа между сообщениями», §3).
    """
    await state.clear()
    await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)

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

@router_catalog_tasks_list.callback_query(TaskCb.filter(mode='a'), CatalogTasksList.view_active_tasks_student)
async def catalog6(callback: CallbackQuery, state: FSMContext, callback_data: TaskCb):
    try:
        await callback.answer()
        task_id = callback_data.task_id
        # §3: задание берём ТОЛЬКО из списка текущего пользователя (callback.from_user.id);
        # кнопка со старого сообщения с чужим task_id даст "Задание не найдено".
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if not selected_task:
            await callback.message.answer("Задание не найдено.")
            return
        await state.update_data(selected_task_id=task_id, ctx_owner=callback.from_user.id)
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}", reply_markup=keyboard_catalog_tasks_list_student_pass.markup)
        await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog6: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'view_passed_tasks_student')
async def catalog14(callback: CallbackQuery, state: FSMContext):
    try:
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 0]:
            await callback.message.answer(f"Ваши завершенные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsd_{callback.from_user.id}').generate_keyboard())
            await state.set_state(CatalogTasksList.view_passed_tasks_student)

        else:
            await callback.message.answer("У вас нет завершенных заданий")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog14: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_active_tasks_teacher')
async def catalog18(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        # §3: id_student из FSM принадлежит тому, кто его записал (catalog17)
        check_ctx_owner(data, callback.from_user.id)
        ensure_student_of_teacher(data['id_student'], callback.from_user.id)
        id_student = int(data['id_student'])
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 1]:
            await callback.message.answer(f"Активные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsa_{id_student}').generate_keyboard())
            await state.set_state(CatalogTasksList.view_active_tasks_teacher)
        else:
            await callback.message.answer("Нет активных заданий.")
    except AccessError as e:
        await callback.answer()
        await callback.message.answer(e.user_message)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog18: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_passed_tasks_teacher')
async def catalog20(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        # §3: id_student из FSM принадлежит тому, кто его записал (catalog17)
        check_ctx_owner(data, callback.from_user.id)
        ensure_student_of_teacher(data['id_student'], callback.from_user.id)
        id_student = int(data['id_student'])
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == 0]:
            await callback.message.answer(f"Завершенные задания", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsd_{id_student}').generate_keyboard())
            await state.set_state(CatalogTasksList.view_passed_tasks_teacher)
        else:
            await callback.message.answer("Нет завершенных заданий.")
    except AccessError as e:
        await callback.answer()
        await callback.message.answer(e.user_message)
        await state.clear()
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
            await state.set_state(CatalogTasksList.view_check_tasks_student)
        else:
            await callback.message.answer("У вас нет заданий на проверке")
    except Exception as e:
        logging.error(f"Ошибка в функции catalog28: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'view_check_tasks_teacher')
async def catalog30(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        # §3: id_student из FSM принадлежит тому, кто его записал (catalog17)
        check_ctx_owner(data, callback.from_user.id)
        ensure_student_of_teacher(data['id_student'], callback.from_user.id)
        id_student = int(data['id_student'])
        student = Student()
        student.get_students_tasks(id_student)
        await callback.answer()
        if [x for x in student.homework_active if x['is_active'] == -1]:
            await callback.message.answer(f"Задания на проверке", reply_markup=DinamicKeyboard(1,3,'no',0,f'tsp_{id_student}').generate_keyboard())
            await state.set_state(CatalogTasksList.view_check_tasks_teacher)
        else:
            await callback.message.answer("Нет заданий на проверке.")
    except AccessError as e:
        await callback.answer()
        await callback.message.answer(e.user_message)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog30: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'add_text_to_task',
                                          StateFilter(CatalogTasksList.view_active_tasks_student,
                                                                      CatalogTasksList.add_file_done))
async def catalog7(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пришлите текст для добавления к заданию '
                                      '(или нажмите «❌ Отменить»)',
                                      reply_markup=keyboard_catalog_tasks_list_cancel_input.markup)
        await state.set_state(CatalogTasksList.add_text_to_task)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog7: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'cancel_add_text')
async def catalog_cancel_add_text(callback: CallbackQuery, state: FSMContext):
    """Отмена ввода текста ответа: обязательный сброс экрана (§2)."""
    try:
        await callback.answer()
        await reset_flow(state)
        await callback.message.answer('Добавление текста отменено.',
                                       reply_markup=keyboard_catalog_tasks_list_student.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog_cancel_add_text: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.message(CatalogTasksList.add_text_to_task, F.text.lower() == 'отмена')
@router_catalog_tasks_list.message(CatalogTasksList._return, F.text.lower() == 'отмена')
async def catalog_cancel_by_text(message: Message, state: FSMContext):
    """Слово «Отмена» прерывает любой ввод-флоу этого роутера и снимает состояние."""
    await reset_flow(state)
    await message.answer('Операция отменена', reply_markup=keyboard_student_start.markup)

@router_catalog_tasks_list.message(CatalogTasksList.add_text_to_task)
async def catalog8(message: Message, state: FSMContext):
    try:
        # §3: черновик принадлежит тому, кто открыл экран (message.from_user.id —
        # реальный отправитель); старый экран в чужом чате сюда не матчится
        check_ctx_owner(await state.get_data(), message.from_user.id)
        await state.update_data(added_text=message.text)
        await message.answer('Текст успешно добавлен к заданию.')
        await special_function(message, state)
        await reset_flow(state)  # экран закрыт — больше не ловим текстовые сообщения (add_text_to_task)
    except AccessError as e:
        await message.answer(e.user_message)
        await reset_flow(state)
    except AccessError as e:
        await message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog8: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'add_file_to_task',
                                          StateFilter(CatalogTasksList.view_active_tasks_student,
                                                                      CatalogTasksList.add_file_done))
async def catalog9(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Пришлите файл для добавления к решению/ответу '
                                      '(или нажмите «❌ Отменить»)',
                                      reply_markup=keyboard_catalog_tasks_list_cancel_input.markup)
        await state.set_state(CatalogTasksList.add_file_to_task)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog9: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.message(F.photo, CatalogTasksList.add_file_to_task)
async def handle_photo_or_album(message: Message, state: FSMContext, bot):
    try:
        # §3: фото/альбом принимает только владелец FSM-черновика (реальный отправитель)
        check_ctx_owner(await state.get_data(), message.from_user.id)
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
                        StatesGroup=CatalogTasksList
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
            await reset_flow(state)  # файл принят — экран ввода закрываем (§2)


    except AccessError as e:
        await message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в handle_photo_or_album: {e}")
        await message.answer("❌ Ошибка при обработке фото")
        await special_function(message, state)
        await reset_flow(state)


@router_catalog_tasks_list.message((F.document | F.photo | F.video | F.audio), CatalogTasksList.add_file_to_task)
async def catalog10(message: Message, state: FSMContext, bot: Bot):
    try:
        # §3: файл принимает только владелец FSM-черновика (реальный отправитель)
        check_ctx_owner(await state.get_data(), message.from_user.id)
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
            await reset_flow(state)
            return
        if file_data.__sizeof__() > 10500000:
            await message.answer("Файл слишком большой, максимальный размер файла 10 МБ.")
            await special_function(message, state)
            await reset_flow(state)
        else:
            await state.update_data(file_name=file_name, file_type=file_type, file_data=file_data)
            await message.answer('Файл прикреплен')
            await special_function(message, state)
            await reset_flow(state)
    except AccessError as e:
        await message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog10: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

async def special_function(message: Message, state: FSMContext):
    """Экран «активное задание ученика» после добавления текста/файла к ответу."""
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
        await message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}", reply_markup=keyboard_catalog_tasks_list_student_pass.markup)
    else:
        await message.answer("Задание не найдено.")


async def special_function_callback_not_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    # §3: экран перерисовываем только владельцу FSM-контекста; чужой ctx_owner — отказ.
    check_ctx_owner(data, callback.from_user.id)
    task_id = data['selected_task_id']
    student = Student()
    student.get_students_tasks(int(data['id_student']))
    selected_task = [task for task in student.homework_active if task['id'] == task_id]
    if selected_task:
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        await callback.message.answer(f"Id задания: {selected_task[0]['id']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}", reply_markup=keyboard_catalog_tasks_list_teacher_check.markup)
    else:
        await callback.message.answer("Задание не найдено.")


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
        await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}", reply_markup=keyboard_catalog_tasks_list_student_pass.markup)
    else:
        await callback.message.answer("Задание не найдено.")

async def special_function_teacher(callback: CallbackQuery, state: FSMContext, bot: Bot, selected_task, callback_data):
    if selected_task:
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        if selected_task[0]['answer_file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к ответу')
        if selected_task[0]['marks'] != None:
            if callback_data == 'set_marks_pased_task':
                data = set_pass((await state.get_data())['selected_task_id'])[0]
                await bot.send_message(data['id_student'], f'Вам изменили оценку на {data["marks"]} по дз на {data["deadline"]}')
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}", reply_markup=keyboard_catalog_tasks_list_teacher_check_passed_task.markup)
            elif callback_data == 'set_marks':
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}", reply_markup=keyboard_catalog_tasks_list_teacher_check.markup)
        else:
            if callback_data == 'set_marks_pased_task':
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}", reply_markup=keyboard_catalog_tasks_list_teacher_check_passed_task.markup)
            elif callback_data == 'set_marks':
                await callback.message.answer(f"Дедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}", reply_markup=keyboard_catalog_tasks_list_teacher_check.markup)
    else:
        await callback.message.answer("Задание не найдено.")












@router_catalog_tasks_list.callback_query(F.data == 'pass_task',
                                          CatalogTasksList.view_active_tasks_student)
async def catalog11(callback: CallbackQuery, state: FSMContext):
    """Шаг подтверждения сдачи — только из экрана активного задания (§2)."""
    try:
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.answer()
            await callback.message.answer('Сессия устарела, откройте «Список заданий» заново',
                                          reply_markup=keyboard_student_start.markup)
            await reset_flow(state)
            return
        await callback.answer()
        await callback.message.edit_text('Вы уверены, что хотите сдать задание?',
                                         reply_markup=keyboard_catalog_tasks_list_confirm_generic.markup)
        await state.set_state(CatalogTasksList.confirm_pass)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog11: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'confirm', CatalogTasksList.confirm_pass)
async def catalog12(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.answer()
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.message.answer('Сессия устарела, откройте «Список заданий» заново',
                                          reply_markup=keyboard_student_start.markup)
            await reset_flow(state)
            return
        # §3: сдавать можно только СВОЁ задание: сверка ctx_owner + владельца задачи.
        check_ctx_owner(data, callback.from_user.id)
        task_row = ensure_task_for_student(get_task_row(data['selected_task_id']), callback.from_user.id)
        if data.get('added_text') == None:
            await callback.message.answer('Прикрепите текст ответа сначала')
            await special_function_callback(callback, state)
            await state.set_state(CatalogTasksList.view_active_tasks_student)
        elif get_is_active(task_row['id']) != 1:
            await callback.message.answer("Задание уже сдано", reply_markup=keyboard_student_start.markup)
            await reset_flow(state)
        else:
            saved = save_answer_task(
                id_task=task_row['id'],
                answer_text=data['added_text'],
                answer_file_name=data['file_name'],
                answer_file_type=data['file_type'],
                answer_file_data=data['file_data'],
                id_student=callback.from_user.id  # §3.5: владелец в WHERE — чужая запись не обновится
            )
            if not saved:
                await callback.message.answer("Задание не найдено или уже изменено, начните заново",
                                              reply_markup=keyboard_student_start.markup)
                await reset_flow(state)
                return
            await callback.message.answer('Задание сдано преподавателю. Ожидайте проверки.', reply_markup=keyboard_student_start.markup)
            student = Student()
            student.get_statistics(callback.from_user.id)
            date = task_row['deadline']
            await bot.send_message(get_id_teacher(task_row['id']), f"Ученик {student.name_student['name']} сдал(а) задание, заданное на {date}. Проверьте его.")
            await reset_flow(state)  # терминальный шаг флоу сдачи (§2)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog12: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        await reset_flow(state)

@router_catalog_tasks_list.callback_query(F.data == 'cancel', CatalogTasksList.confirm_pass)
async def catalog13(callback: CallbackQuery, state: FSMContext):
    """Отмена сдачи возвращает пользователя в экран активного задания и снимает
    состояние подтверждения — кнопки «Подтвердить/Отменить» больше не живые (§2)."""
    try:
        await callback.answer()
        await reset_flow(state)
        await callback.message.answer('Сдача задания отменена.',
                                      reply_markup=keyboard_catalog_tasks_list_student.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog13: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        await reset_flow(state)


@router_catalog_tasks_list.callback_query(TaskCb.filter(mode='d'), CatalogTasksList.view_passed_tasks_student)
async def catalog15(callback: CallbackQuery, state: FSMContext, callback_data: TaskCb):
    try:
        await callback.answer()
        task_id = callback_data.task_id
        # §3: только задачи текущего ученика (см. catalog6)
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if not selected_task:
            await callback.message.answer("Задание не найдено.")
            return
        await state.update_data(selected_task_id=task_id, ctx_owner=callback.from_user.id)
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        if selected_task[0]['answer_file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
        if selected_task[0]['marks'] != None:
            await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\n\nОценка: {selected_task[0]['marks']}")
        else:
            await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}")

        await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog15: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(StudentCb.filter(mode='view'))
async def catalog17(callback: CallbackQuery, state: FSMContext, callback_data: StudentCb):
    try:
        await reset_flow(state)  # новый флоу: не переносим selected_task_id/черновики прошлого экрана (§2)
        # §3: ученик обязан состоять в списке ТЕКУЩЕГО учителя — иначе кнопка со
        # старого сообщения даёт доступ к чужому ученику.
        ensure_student_of_teacher(callback_data.student_id, callback.from_user.id)
        await state.update_data(id_student=callback_data.student_id, ctx_owner=callback.from_user.id)
        await callback.answer()
        student = Student()
        student.get_statistics(callback_data.student_id)
        name = student.name_student['name'] if student.name_student else 'Неизвестно'
        await callback.message.answer(f'Ученик: {name} (id ученика: {callback_data.student_id})\nВыберите', reply_markup=keyboard_catalog_tasks_list_teacher.markup)
    except AccessError as e:
        await callback.answer()
        await callback.message.answer(e.user_message)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog17: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(TaskCb.filter(mode='a'), CatalogTasksList.view_active_tasks_teacher)
async def catalog19(callback: CallbackQuery, state: FSMContext, callback_data: TaskCb):
    try:
        await callback.answer()
        task_id = callback_data.task_id
        data = await state.get_data()
        # §3: сверяем FSM-контекст с текущим учителем и составом его списка
        check_ctx_owner(data, callback.from_user.id)
        id_student = int(data['id_student'])
        ensure_student_of_teacher(id_student, callback.from_user.id)
        # §3: задание берём только из списка выбранного ученика — чужой task_id отклоняется
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if not selected_task:
            await callback.message.answer("Задание не найдено.")
            return
        await state.update_data(selected_task_id=task_id)
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        await callback.message.answer(f"Id задания: {selected_task[0]['id']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}", reply_markup=keyboard_catalog_tasks_list_teacher_check.markup)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog19: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(TaskCb.filter(mode='d'), CatalogTasksList.view_passed_tasks_teacher)
async def catalog21(callback: CallbackQuery, state: FSMContext, callback_data: TaskCb):
    try:
        await callback.answer()
        data = await state.get_data()
        # §3: сверяем FSM-контекст с текущим учителем и составом его списка
        check_ctx_owner(data, callback.from_user.id)
        id_student = int(data['id_student'])
        ensure_student_of_teacher(id_student, callback.from_user.id)
        task_id = callback_data.task_id
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if not selected_task:
            await callback.message.answer("Задание не найдено.")
            return
        await state.update_data(selected_task_id=task_id)
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        if selected_task[0]['answer_file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
        if selected_task[0]['marks'] != None:
            await callback.message.answer(f"Id задания: {selected_task[0]['id']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}", reply_markup=keyboard_catalog_tasks_list_teacher_check_passed_task.markup)
        else:
            await callback.message.answer(f"Id задания: {selected_task[0]['id']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}", reply_markup=keyboard_catalog_tasks_list_teacher_check_passed_task.markup)

    except AccessError as e:
        await callback.message.answer(e.user_message)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog21: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'set_marks',
                                          CatalogTasksList.view_check_tasks_teacher)
async def catalog22(callback: CallbackQuery, state: FSMContext):
    """Экран выбора оценки — только из «Заданий на проверке» (§2)."""
    try:
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.answer()
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        await callback.answer()
        await callback.message.edit_text('Выберите оценку', reply_markup=keyboard_choice_marks.markup)
        await state.update_data(callback_data='set_marks')
        await state.set_state(CatalogTasksList.set_mark)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog22: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'set_marks_pased_task',
                                          CatalogTasksList.view_passed_tasks_teacher)
async def catalog23(callback: CallbackQuery, state: FSMContext):
    """Экран смены оценки — только из «Завершенных» (§2)."""
    try:
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.answer()
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        await callback.answer()
        await callback.message.edit_text('Выберите оценку', reply_markup=keyboard_choice_marks.markup)
        await state.update_data(callback_data='set_marks_pased_task')
        await state.set_state(CatalogTasksList.set_mark)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog23: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(MarkCb.filter(), CatalogTasksList.set_mark)
async def catalog24(callback: CallbackQuery, state: FSMContext, bot: Bot, callback_data: MarkCb):
    try:
        await callback.answer()
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        # §3: оценку ставит только учитель-владелец FSM-контекста и самой задачи
        check_ctx_owner(data, callback.from_user.id)
        ensure_task_for_teacher(get_task_row(data['selected_task_id']), callback.from_user.id)
        set_marks(data['selected_task_id'], callback_data.value, id_teacher=callback.from_user.id)
        await callback.message.answer('Оценка установлена')
        id_student = int(data['id_student'])
        task_id = data['selected_task_id']
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        saved_callback_data = data.get('callback_data')
        await special_function_teacher(callback, state, bot, selected_task, saved_callback_data)
        await reset_flow(state)  # оценка выставлена — терминальный шаг экрана (§2)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog24: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        await reset_flow(state)

@router_catalog_tasks_list.callback_query(F.data == 'set_passed',
                                          StateFilter(CatalogTasksList.view_check_tasks_teacher,
                                                      CatalogTasksList.view_passed_tasks_teacher))
async def catalog25(callback: CallbackQuery, state: FSMContext):
    """Экран подтверждения отметки «решено» — собственный FSM-экран (§2).

    Раньше здесь ставилось view_passed_tasks_teacher, и кнопка «✅ Подтвердить»
    из общего колбэка 'confirm' матчилась без состояния — живой кнопкой из
    старого сообщения действие можно было повторить или подтвердить чужой экран.
    """
    try:
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.answer()
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        await callback.answer()
        await callback.message.answer('Вы уверены?',
                                      reply_markup=keyboard_catalog_tasks_list_confirm_generic.markup)
        await state.set_state(CatalogTasksList.confirm_set_passed)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog25: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'confirm', CatalogTasksList.confirm_set_passed)
async def catalog26(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        await callback.answer()
        data = await state.get_data()
        if data.get('selected_task_id') is None:
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        # §3: «решено» ставит только учитель-владелец FSM-контекста и самой задачи
        check_ctx_owner(data, callback.from_user.id)
        ensure_task_for_teacher(get_task_row(data['selected_task_id']), callback.from_user.id)
        if get_is_active(data['selected_task_id']) != -1:
            await callback.message.answer("Задание уже отмеченно как завершенное",
                                          reply_markup=keyboard_teacher_start.markup)
        else:
            result = set_pass(data['selected_task_id'], id_teacher=callback.from_user.id)
            if not result:
                await callback.message.answer('❌Задание не найдено',
                                              reply_markup=keyboard_teacher_start.markup)
            else:
                task = result[0]
                await callback.message.answer('Задание отмечено как завершенное',
                                              reply_markup=keyboard_teacher_start.markup)
                mark_text = f"Вам выставили оценку {task['marks']}" if task['marks'] is not None \
                    else "Ваша работа принята"
                await bot.send_message(task['id_student'],
                                       f"{mark_text} по дз на {task['deadline']}")
        await reset_flow(state)  # терминальный шаг (§2)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog26: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        await reset_flow(state)

@router_catalog_tasks_list.callback_query(F.data == 'cancel', CatalogTasksList.confirm_set_passed)
async def catalog27(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Отмена — возврат в экран задания с обязательным снятием состояния подтверждения (§2)."""
    try:
        await callback.answer()
        data = await state.get_data()
        id_student = data.get('id_student')
        task_id = data.get('selected_task_id')
        if id_student is None or task_id is None:
            await reset_flow(state)
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            return
        # §3: данные экрана принадлежат текущему учителю, ученик — в его списке
        check_ctx_owner(data, callback.from_user.id)
        ensure_student_of_teacher(id_student, callback.from_user.id)
        student = Student()
        student.get_students_tasks(int(id_student))
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        callback_data = data.get('callback_data')
        await special_function_teacher(callback, state, bot, selected_task, callback_data)
        await state.update_data(callback_data=None)  # черновик не переносим на следующий экран (§2)
        await state.set_state(CatalogTasksList.view_check_tasks_teacher)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog27: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(TaskCb.filter(mode='p'), CatalogTasksList.view_check_tasks_student)
async def catalog29(callback: CallbackQuery, state: FSMContext, callback_data: TaskCb):
    try:
        await callback.answer()
        task_id = callback_data.task_id
        # §3: только задачи текущего ученика (см. catalog6)
        student = Student()
        student.get_students_tasks(callback.from_user.id)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if not selected_task:
            await callback.message.answer("Задание не найдено.")
            return
        await state.update_data(selected_task_id=task_id, ctx_owner=callback.from_user.id)
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        if selected_task[0]['answer_file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
        if selected_task[0]['marks'] != None:
            await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}")
        else:
            await callback.message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}")

        await state.update_data(added_text=None, file_name=None, file_type=None, file_data=None)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog29: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(TaskCb.filter(mode='p'), CatalogTasksList.view_check_tasks_teacher)
async def catalog31(callback: CallbackQuery, state: FSMContext, callback_data: TaskCb):
    try:
        await callback.answer()
        data = await state.get_data()
        # §3: сверяем FSM-контекст с текущим учителем и составом его списка
        check_ctx_owner(data, callback.from_user.id)
        id_student = int(data['id_student'])
        ensure_student_of_teacher(id_student, callback.from_user.id)
        task_id = callback_data.task_id
        student = Student()
        student.get_students_tasks(id_student)
        selected_task = [task for task in student.homework_active if task['id'] == task_id]
        if not selected_task:
            await callback.message.answer("Задание не найдено.")
            return
        await state.update_data(selected_task_id=task_id)
        teacher = Teacher()
        teacher.get_statistics(selected_task[0]['id_teacher'])
        if selected_task[0]['file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['file_data'], filename=selected_task[0]['file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к заданию')
        if selected_task[0]['answer_file_name'] != None:
            document_to_send = BufferedInputFile(file=selected_task[0]['answer_file_data'], filename=selected_task[0]['answer_file_name'])
            await callback.message.answer_document(document=document_to_send, caption='Файл к вашему ответу')
        if selected_task[0]['marks'] != None:
            await callback.message.answer(f"Id задания: {selected_task[0]['id']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}\nОценка: {selected_task[0]['marks']}", reply_markup=keyboard_catalog_tasks_list_teacher_check.markup)
        else:
            await callback.message.answer(f"Id задания: {selected_task[0]['id']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}\n\nТекст ответа: {selected_task[0]['answer_text']}", reply_markup=keyboard_catalog_tasks_list_teacher_check.markup)

    except AccessError as e:
        await callback.message.answer(e.user_message)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции catalog31: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(F.data == 'change_deadline',
                                          StateFilter(CatalogTasksList.view_check_tasks_teacher,
                                                      CatalogTasksList.view_active_tasks_teacher))
async def catalog32(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Выберите новый дедлайн', inline_message_id=callback.inline_message_id, reply_markup = await SimpleCalendar().start_calendar())
        await state.set_state(CatalogTasksList.change_deadline)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog32: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        

@router_catalog_tasks_list.callback_query(SimpleCalendarCallback.filter(), CatalogTasksList.change_deadline)
async def catalog33(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    try:
        if callback_data.act == simple_calendar.SimpleCalAct.cancel:
            await special_function_callback_not_callback(callback, state)
        else:
            calendar = SimpleCalendar()
            selected, date = await calendar.process_selection(callback, callback_data)

            if selected:
                await state.update_data(homework_date=str(date))
                await callback.answer()
                await callback.message.edit_text("Выберите дедлайн", reply_markup=keyboard_time_selection.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog33: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_catalog_tasks_list.callback_query(F.data == 'cancel_time_selection', CatalogTasksList.change_deadline)
async def catalog34(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Выберите дату сдачи', inline_message_id=callback.inline_message_id, reply_markup = await SimpleCalendar().start_calendar())
    except Exception as e:
        logging.error(f"Ошибка в функции catalog34: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_catalog_tasks_list.callback_query(TimeCb.filter(), CatalogTasksList.change_deadline)
async def catalog35(callback: CallbackQuery, state: FSMContext, callback_data: TimeCb):
    try:
        data = await state.get_data()
        task_id = data.get('selected_task_id')
        date_str = data.get('homework_date')
        if not task_id or not date_str:
            # защита от «застывшего» экрана: без данных сессии не пишем в БД (§2)
            await callback.answer()
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        # §3: дедлайн меняет только учитель-владелец FSM-контекста и самой задачи
        check_ctx_owner(data, callback.from_user.id)
        ensure_task_for_teacher(get_task_row(task_id), callback.from_user.id)
        hour = f'{callback_data.hour:02d}'
        date_with_time = f"{date_str.split(' ')[0]} {hour}:00:00"

        if not update_deadline(task_id, date_with_time, id_teacher=callback.from_user.id):
            await callback.answer()
            await callback.message.answer('Задание не найдено или уже изменено, начните заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        
        await callback.answer(f"Время обновлено: {date_with_time}")
        await special_function_callback_not_callback(callback, state)
        await reset_flow(state)  # дедлайн изменён — терминальный шаг экрана (§2)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog35: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        await reset_flow(state)

@router_catalog_tasks_list.callback_query(F.data == 'return', CatalogTasksList.view_check_tasks_teacher)
async def catalog36(callback: CallbackQuery, state: FSMContext):
    """«На дорешку» — только из экрана задания на проверке + проверка данных сессии (§2)."""
    try:
        data = await state.get_data()
        if data.get('selected_task_id') is None or data.get('id_student') is None:
            await callback.answer()
            await callback.message.answer('Сессия устарела, откройте список заданий заново',
                                          reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        # §3: «на дорешку» возвращает задание только его учитель-владелец
        check_ctx_owner(data, callback.from_user.id)
        ensure_task_for_teacher(get_task_row(data['selected_task_id']), callback.from_user.id)
        await callback.answer()
        await callback.message.answer('Пришлите коментарий для отправки ученику или «Отмена», что бы отменить')
        await state.set_state(CatalogTasksList._return)
    except AccessError as e:
        await callback.message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog36: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
        
@router_catalog_tasks_list.message(CatalogTasksList._return)
async def catalog37(message: Message, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        task_id = data.get('selected_task_id')
        id_student = data.get('id_student')
        if not task_id or not id_student:
            await message.answer('Сессия устарела, откройте список заданий заново',
                                 reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        # §3: комментарий уходит только если задача принадлежит этому учителю
        # (message.from_user.id — реальный отправитель, не данные из FSM)
        check_ctx_owner(data, message.from_user.id)
        ensure_task_for_teacher(get_task_row(task_id), message.from_user.id)
        rows = get_date(task_id)
        if not rows:
            await message.answer('Задание не найдено', reply_markup=keyboard_teacher_start.markup)
            await reset_flow(state)
            return
        date = rows[0]['deadline']
        text = message.text
        if text.strip().lower() in ('none', 'отмена'):
            await message.answer("Операция отменена", reply_markup=keyboard_teacher_start.markup)
        else:
            if not return_goback(task_id, id_teacher=message.from_user.id):
                await message.answer('Задание не найдено или уже изменено, начните заново',
                                     reply_markup=keyboard_teacher_start.markup)
                await reset_flow(state)
                return
            await message.answer("Задание отправлено на дорешку, комментарий отправлен ученику", reply_markup=keyboard_teacher_start.markup)
            await bot.send_message(chat_id=id_student, text=f"Задание на {date} было отправлено на дорешку с комментарием преподавателя:\n\n{text}")
        await reset_flow(state)  # терминальный шаг «на дорешку» (§2)
    except AccessError as e:
        await message.answer(e.user_message)
        await reset_flow(state)
    except Exception as e:
        logging.error(f"Ошибка в функции catalog37: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')
        await reset_flow(state)