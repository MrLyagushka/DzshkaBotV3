from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_TASK

def save_task(id_teacher: int, id_student: int, text: str, file_name: str, file_type: str, file_data: bytes, homework_date: str):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO task (id_teacher, id_student, text, file_name, file_type, file_data, deadline) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (id_teacher, id_student, text, file_name, file_type, file_data, homework_date)
            )
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции save_task: {e}")