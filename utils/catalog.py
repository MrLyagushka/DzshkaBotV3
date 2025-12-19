from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_TASK, PATH_TO_DB_USERS

def add_student(id_student: int, id_teacher: int):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("UPDATE student SET id_teacher = ? WHERE id = ?", (id_teacher, id_student,))
            db.commit()
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции add_student: {e}")

def save_answer_task(id_task: int, answer_text: str, answer_file_name: str | None, answer_file_type: str | None, answer_file_data: bytes | None):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute(
                "UPDATE task SET answer_text = ?, answer_file_name = ?, answer_file_type = ?, answer_file_data = ?, is_active = ? WHERE id = ?",
                (answer_text, answer_file_name, answer_file_type, answer_file_data, -1, id_task)
            )
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции save_answer_task: {e}")

def get_id_teacher(id_task: int):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id_teacher FROM task WHERE id = ?", (id_task,))
            result = cursor.fetchone()
            if result:
                return result['id_teacher']
            return None
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции get_id_teacher: {e}")
        return None
    
def set_pass(id_task: int):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("UPDATE task SET is_active = ? WHERE id = ?", (0, id_task,))
            cursor.execute("SELECT id_student, deadline, marks FROM task WHERE id = ?", (id_task,))
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции set_pass: {e}")
        return None
    
def set_marks(id_task: int, mark: int):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("UPDATE task SET marks = ? WHERE id = ?", (mark, id_task,))
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции set_marks: {e}")
        return None
    
def update_deadline(id_task: int, new_deadline: str):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("UPDATE task SET deadline = ? WHERE id = ?", (new_deadline, id_task,))
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции update_deadline: {e}")
        return None