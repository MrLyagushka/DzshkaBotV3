from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_TASK

def save_task(id_teacher: int, id_student: int, text: str, file_name: str, file_type: str, file_data: bytes, homework_date: str):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id FROM task")
            if cursor.fetchall():
                last_id = sorted([x['id'] for x in cursor.fetchall()])[-1] + 1
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