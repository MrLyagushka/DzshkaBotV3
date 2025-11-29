from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_USERS
from utils.filter import is_student, is_teacher

def get_user_profile(id: int):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id, username FROM users WHERE id = ?", (id,))
            user_info = cursor.fetchone()
            cursor.execute("SELECT id, username, name, id_teacher FROM student WHERE id = ?", (id,))
            student_info = cursor.fetchone()
            cursor.execute("SELECT id, username, name FROM teacher WHERE id = ?", (id,))
            teacher_info = cursor.fetchone()
            profile = {
                "user": dict(user_info) if user_info else None,
                "student": dict(student_info) if student_info else None,
                "teacher": dict(teacher_info) if teacher_info else None
            }
            return profile
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции get_user_profile: {e}")

def reset_name(id: int, name: str):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id in [x['id'] for x in is_teacher()]:
                cursor.execute("UPDATE teacher SET name = ? WHERE id = ?", (name, id))
            elif id in [x['id'] for x in is_student()]:
                cursor.execute("UPDATE student SET name = ? WHERE id = ?", (name, id))
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции reset_name: {e}")

def reset_registration(id: int):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id in [x['id'] for x in is_teacher()]:
                cursor.execute("DELETE FROM teacher WHERE id = ?", (id,))
            elif id in [x['id'] for x in is_student()]:
                cursor.execute("DELETE FROM student WHERE id = ?", (id,))
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции reset_registration: {e}")