from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_TASK

async def get_task():
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id, id_student, id_teacher, deadline, marks, is_active FROM task WHERE is_active = 1")
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Возникла ошибка при выполнении функции get_task: {e}")

def save_task(id_teacher: int, id_student: int, text: str, file_name: str, file_type: str, file_data: bytes, homework_date: str):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id FROM task")
            result = cursor.fetchall()
            if len(result) != 0:
                last_id = sorted([x['id'] for x in result], reverse=True)[0] + 1
            else:
                last_id = 1
            cursor.execute(
                "INSERT INTO task (id, id_teacher, id_student, text, file_name, file_type, file_data, deadline, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (last_id, id_teacher, id_student, text, file_name, file_type, file_data, homework_date, 1,)
            )
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции save_task: {e}")

def set_marks(id_task: int, marks: int):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute(
                "UPDATE task SET marks = ? WHERE id = ?",
                (marks, id_task,)
            )
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции set_marks: {e}")
