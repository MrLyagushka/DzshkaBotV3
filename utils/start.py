from sqlite3 import connect, Row
import logging
from config import PATH_TO_DB_USERS


def are_you_new_user(id: int):
    """
    Если id нет в базе, то функция вернет 0, иначе функция вернет id. Если функция вернула 1, возникла ошибка при передаче id"""
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id FROM users WHERE id = ?", (id,))
            result = cursor.fetchone()
            if not result:
                return 0
            else:
                cursor.execute("SELECT id FROM student WHERE id = ?", (id,))
                result = cursor.fetchone()
                cursor.execute("SELECT id FROM teacher WHERE id = ?", (id,))
                result2 = cursor.fetchone()
                if not result and not result2:
                    return 0
                if not result:
                    return result2
                if not result2:
                    return result
    except Exception as e:
        logging.error(f"Возникла ошибка при передаче id в функцию are_you_new_user: {e}")
        return 1
    
def add_user_to_db(id: int, username: str):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id FROM users WHERE id = ?", (id,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO users (id, username) VALUES (?, ?)", (id, username,))
    except Exception as e:
        logging.error(f"Возникла ошибка при работе функции add_user_to_db: {e}")
        return 1
    
def add_student_to_db(id: int, username: str, name: str):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("INSERT INTO student (id, username, name) VALUES (?, ?, ?)", (id, username, name))
    except Exception as e:
        logging.error(f"Возникла ошибка в функции add_student_to_db")

def add_teacher_to_db(id: int, username: str, name: str):
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("INSERT INTO teacher (id, username, name) VALUES (?, ?, ?)", (id, username, name))
    except Exception as e:
        logging.error(f"Возникла ошибка в функции add_teacher_to_db")