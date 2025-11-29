from config import PATH_TO_DB_USERS
from sqlite3 import connect, Row
import logging

def is_student():
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id FROM student")
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Произошла ошибка в функции is_student: {e}")   
    
def is_teacher():
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id FROM teacher")
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Произошла ошибка в функции is_teacher: {e}")