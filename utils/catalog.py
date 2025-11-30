from sqlite3 import connect, Row
import logging

def add_student(id_student: int, id_teacher: int):
    try:
        with connect('database.db') as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("UPDATE student SET id_teacher = ? WHERE id_student = ?", (id_teacher, id_student,))
            db.commit()
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции add_student: {e}")