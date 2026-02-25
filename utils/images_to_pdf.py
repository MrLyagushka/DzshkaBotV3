from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile
from aiogram import Bot
import asyncio
import logging
import io
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

from keyboards.catalog import keyboard_catalog_student_pass
from keyboards.homework import keyboard_homework
from utils.users import Teacher, Student


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
        await message.answer(f"Задание от преподавателя: {teacher.name_teacher['name']}\nДедлайн: {selected_task[0]['deadline']}\n\nТекст задания:\n{selected_task[0]['text']}", reply_markup=keyboard_catalog_student_pass.markup)
    else:
        await message.answer("Задание не найдено.")


def images_to_pdf(image_bytes_list: list[bytes]) -> bytes:
    """
    Принимает список байтов изображений, возвращает байты PDF.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    for img_bytes in image_bytes_list:
        try:
            # Открываем изображение из байтов
            img = Image.open(io.BytesIO(img_bytes))
            img = img.convert("RGB")  # Убираем альфа-канал (если есть)

            # Масштабируем под размер страницы A4 с сохранением пропорций
            img_width, img_height = img.size
            scale = min(width / img_width, height / img_height)
            new_width = img_width * scale
            new_height = img_height * scale

            x = (width - new_width) / 2
            y = (height - new_height) / 2

            # Рисуем изображение на странице
            img_reader = ImageReader(img)
            c.drawImage(img_reader, x, y, new_width, new_height)
            c.showPage()  # Новая страница для следующего изображения
        except Exception as e:
            print(f"Ошибка при обработке изображения: {e}")
            continue

    c.save()
    buffer.seek(0)
    return buffer.read()

async def process_album_after_timeout(message: Message, state: FSMContext, bot: Bot, chat_id: int, expected_media_group_id: str, Homework):
    """Фоновая функция: ждёт 2 сек, проверяет, закончился ли альбом, и конвертирует в PDF."""
    await asyncio.sleep(2)  # дать время на приход всех фото

    data = await state.get_data()

    # Проверяем: альбом всё ещё актуален?
    if data.get("current_album_id") != expected_media_group_id:
        return  # уже другой альбом → игнорируем

    file_ids = data.get("album_photos", [])
    if not file_ids:
        return

    # Скачиваем все фото
    photo_bytes_list = []
    for file_id in file_ids:
        try:
            file = await bot.get_file(file_id)
            # === Безопасное получение file_bytes ===
            file_data = await bot.download_file(file.file_path)
            file_bytes = file_data.read() if hasattr(file_data, 'read') else file_data
            photo_bytes_list.append(file_bytes)
        except Exception as e:
            logging.warning(f"Не удалось скачать фото {file_id}: {e}")

    if not photo_bytes_list:
        await bot.send_message(chat_id, "❌ Не удалось загрузить фото для альбома.")
        return

    # Конвертируем в PDF
    from utils.images_to_pdf import images_to_pdf
    try:
        pdf_bytes = images_to_pdf(photo_bytes_list)
    except Exception as e:
        logging.error(f"Ошибка конвертации в PDF: {e}")
        await bot.send_message(chat_id, "❌ Ошибка при создании PDF.")
        return

    # Сохраняем в state и уведомляем
    await state.update_data(
        file_name="homework_album.pdf",
        file_type="document",
        file_data=pdf_bytes,
        current_album_id=None,
        album_photos=[],
        waiting_for_album=False
    )
    await bot.send_message(chat_id, "Файл успешно прикреплен")
    await special_function(message, state)


async def process_album_after_timeout2(message: Message, state: FSMContext, bot: Bot, chat_id: int, expected_media_group_id: str, Homework):
    """Фоновая функция: ждёт 2 сек, проверяет, закончился ли альбом, и конвертирует в PDF."""
    await asyncio.sleep(2)  # дать время на приход всех фото

    data = await state.get_data()

    # Проверяем: альбом всё ещё актуален?
    if data.get("current_album_id") != expected_media_group_id:
        return  # уже другой альбом → игнорируем

    file_ids = data.get("album_photos", [])
    if not file_ids:
        return

    # Скачиваем все фото
    photo_bytes_list = []
    for file_id in file_ids:
        try:
            file = await bot.get_file(file_id)
            # === Безопасное получение file_bytes ===
            file_data = await bot.download_file(file.file_path)
            file_bytes = file_data.read() if hasattr(file_data, 'read') else file_data
            photo_bytes_list.append(file_bytes)
        except Exception as e:
            logging.warning(f"Не удалось скачать фото {file_id}: {e}")

    if not photo_bytes_list:
        await bot.send_message(chat_id, "❌ Не удалось загрузить фото для альбома.")
        return

    # Конвертируем в PDF
    from utils.images_to_pdf import images_to_pdf
    try:
        pdf_bytes = images_to_pdf(photo_bytes_list)
    except Exception as e:
        logging.error(f"Ошибка конвертации в PDF: {e}")
        await bot.send_message(chat_id, "❌ Ошибка при создании PDF.")
        return

    # Сохраняем в state и уведомляем
    await state.update_data(
        file_name="homework_album.pdf",
        file_type="document",
        file_data=pdf_bytes,
        current_album_id=None,
        album_photos=[],
        waiting_for_album=False
    )
    await bot.send_message(chat_id, "Файл успешно прикреплен", reply_markup=keyboard_homework.markup)
    await state.set_state(Homework.second)