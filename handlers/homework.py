from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram_calendar import SimpleCalendarCallback, SimpleCalendar, simple_calendar
import logging

from handlers.start import Start
from keyboards.homework import keyboard_homework, keyboard_homework_confirmation, keyboard_time_selection, keyboard_homework_add_file
from keyboards.start import keyboard_teacher_start
from utils.template import DinamicKeyboard
from utils.homework import save_task
from utils.users import Teacher
from utils.images_to_pdf import process_album_after_timeout, process_album_after_timeout2
import asyncio

class Homework(StatesGroup):
    first = State()
    second = State()
    third = State()
    fourth = State()
    fifth = State()

router_homework = Router()

@router_homework.message(F.text == 'Выдать задание')
async def homework0(message: Message, state: FSMContext):
    try:
        teacher = Teacher()
        teacher.get_statistics(message.from_user.id)
        if teacher.students_info:
            await message.answer('Выберите ученика для выдачи задания', reply_markup=DinamicKeyboard(1,3,'no',0,f'st_{message.from_user.id}').generate_keyboard())
            await state.set_state(Homework.first)
        else:
            await message.answer('У вас нет учеников. Прикрепите ученика через "Список учеников"->"Добавить ученика"', reply_markup=keyboard_teacher_start.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции homework0: {e}")
        message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(F.data[:13]=='callback_data', Homework.first)
async def homework1(callback: CallbackQuery, state: FSMContext):
    try:
        await state.update_data(student_id=int(callback.data.split('_')[4]))
        await callback.answer()
        await callback.message.answer('Пришлите текст задания')
        await state.set_state(Homework.fifth)
    except Exception as e:
        logging.error(f"Ошибка в функции homework1: {e}")
        callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.message(Homework.fifth)
async def homework2(message: Message, state: FSMContext):
    try:
        await state.update_data(homework_text=message.text)
        await message.answer('Текст задания установлен', reply_markup=keyboard_homework.markup)
        await state.update_data(homework_date=0)
        await state.set_state(Homework.second)
    except Exception as e:
        logging.error(f"Ошибка в функции homework2: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(F.data == 'send_file', Homework.second)
async def homework3(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Пришлите файл с заданием', inline_message_id=callback.inline_message_id)
        await callback.message.edit_reply_markup(reply_markup=keyboard_homework_add_file.markup)
        await state.set_state(Homework.third)
    except Exception as e:
        logging.error(f"Ошибка в функции homework3: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(F.data == 'cancel_to_homework', Homework.third)
async def homework4(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Выберите', inline_message_id=callback.inline_message_id)
        await callback.message.edit_reply_markup(reply_markup=keyboard_homework.markup)
        await state.set_state(Homework.second)
    except Exception as e:
        logging.error(f"Ошибка в функции homework4: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.message(F.photo, Homework.third)
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
                    process_album_after_timeout2(
                        message=message,
                        state=state,
                        bot=bot,
                        chat_id=message.chat.id,
                        expected_media_group_id=media_group_id,
                        Homework=Homework
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
            await message.answer("Фото прикреплено", reply_markup=keyboard_homework.markup)
            await state.set_state(Homework.second)

    except Exception as e:
        logging.error(f"Ошибка в handle_photo_or_album: {e}")
        await message.answer("❌ Ошибка при обработке фото", reply_markup=keyboard_homework.markup)

@router_homework.message(F.photo, Homework.third)
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
                        state=state,
                        bot=bot,
                        chat_id=message.chat.id,
                        media_group_id=media_group_id
                    )
                )
                # Ничего не отвечаем сразу — пользователь увидит сообщение позже
                return

        # === Сценарий 2: одиночное фото ===
        else:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            # === Безопасное получение file_bytes ===
            file_data = await bot.download_file(file.file_path)
            file_bytes = file_data.read() if hasattr(file_data, 'read') else file_data

            await state.update_data(
                file_name="photo.jpg",
                file_type="photo",
                file_data=file_bytes
            )
            await message.answer("Фото прикреплено", reply_markup=keyboard_homework.markup)
            await state.set_state(Homework.second)

    except Exception as e:
        logging.error(f"Ошибка в handle_photo_or_album: {e}")
        await message.answer("❌ Ошибка при обработке фото", reply_markup=keyboard_homework.markup)

@router_homework.message((F.document | F.video | F.audio), Homework.third)
async def homework4(message: Message, state: FSMContext, bot: Bot):
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
            await message.answer("Поддерживаются только: фото, документы, видео, аудио.", reply_markup=keyboard_homework.markup)
        if file_data.__sizeof__() > 10500000:
            await message.answer("Файл слишком большой, максимальный размер файла 10 МБ.", reply_markup=keyboard_homework.markup)
        else:
            await state.update_data(file_name=file_name, file_type=file_type, file_data=file_data)
            await message.answer('Файл прикреплен', reply_markup=keyboard_homework.markup)
            await state.set_state(Homework.second)

    except Exception as e:
        logging.error(f"Ошибка в функции homework4: {e}")
        await message.answer('❌Ошибка, обратитесь в поддержку')
    
@router_homework.callback_query(F.data == 'set_date', Homework.second)
async def homework5(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Выберите дату сдачи', inline_message_id=callback.inline_message_id, reply_markup = await SimpleCalendar().start_calendar())
        await state.set_state(Homework.third)
    except Exception as e:
        logging.error(f"Ошибка в функции homework5: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(SimpleCalendarCallback.filter(), Homework.third)
async def homework6(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext
):
    try:
        if callback_data.act == simple_calendar.SimpleCalAct.cancel:
            await callback.message.answer('Выберите', reply_markup=keyboard_homework.markup)
            await state.set_state(Homework.second)
        else:
            calendar = SimpleCalendar()
            selected, date = await calendar.process_selection(callback, callback_data)

            if selected:
                await state.set_state(Homework.fourth)
                await state.update_data(homework_date=str(date))
                await callback.answer()
                await callback.message.edit_text("Выберите дедлайн", reply_markup=keyboard_time_selection.markup)

    except Exception as e:
        logging.error(f"Ошибка в функции homework6: {e}")
        await callback.message.answer("❌ Ошибка, обратитесь в поддержку")

@router_homework.callback_query(F.data[:4] == 'time', Homework.fourth)
async def homework7(callback: CallbackQuery, state: FSMContext):
    try:
        hour = callback.data.split('_')[1]
        data = await state.get_data()
        date_str = data['homework_date']
        date_with_time = f"{date_str.split(' ')[0]} {hour}:00:00"
        await state.update_data(homework_date=date_with_time)
        await callback.answer(f"Время установлено: {date_with_time}")
        await callback.message.edit_text("Время сдачи установлено", reply_markup=keyboard_homework.markup)
        await state.set_state(Homework.second)
    except Exception as e:
        logging.error(f"Ошибка в функции homework7: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(F.data == 'cancel_time_selection', Homework.fourth)
async def homework8(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text('Выберите дату сдачи', inline_message_id=callback.inline_message_id, reply_markup = await SimpleCalendar().start_calendar())
        await state.set_state(Homework.third)
    except Exception as e:
        logging.error(f"Ошибка в функции homework5: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')


@router_homework.callback_query(F.data == 'send_homework', Homework.second)
async def homework9(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.edit_text("Подтвердите отправку задания", inline_message_id=callback.inline_message_id, reply_markup=keyboard_homework_confirmation.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции homework9: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(F.data == 'confirm_cancel')
async def homework10(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        await callback.message.answer('Дополните задание', reply_markup=keyboard_homework.markup)
    except Exception as e:
        logging.error(f"Ошибка в функции homework10: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')

@router_homework.callback_query(F.data == 'confirm_send')
async def homework11(callback: CallbackQuery, bot: Bot, state: FSMContext):
    try:
        data = await state.get_data()
        await callback.answer()
        if data['homework_date'] == 0:
            try:
                await callback.message.edit_text("Установите дату сдачи", inline_message_id=callback.inline_message_id, reply_markup=keyboard_homework.markup)
            except Exception as e:
                pass
        else:
            save_task(id_teacher=callback.from_user.id, id_student=data['student_id'], text=data['homework_text'], file_name=data.get('file_name'), file_type=data.get('file_type'), file_data=data.get('file_data'), homework_date=data.get('homework_date'))
            await bot.send_message(chat_id=data['student_id'], text=f"Новое задание!\nДедлайн: {data['homework_date']}")
            await callback.message.answer('Задание отправлено ученику!', reply_markup=keyboard_teacher_start.markup)
            await state.clear()
    except Exception as e:
        logging.error(f"Ошибка в функции homework11: {e}")
        await callback.message.answer('❌Ошибка, обратитесь в поддержку')
