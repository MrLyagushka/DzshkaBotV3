"""Точечные проверки ролей пользователя (§5).

Раньше is_student()/is_teacher() без аргументов грузили ВСЮ таблицу
(SELECT id FROM student/teacher), а хендлеры делали `[x['id'] for x in ...]`
и линейный поиск — O(N) памяти и времени на каждое сообщение. Теперь это
один запрос `SELECT 1 ... WHERE id = ?` (O(1)) с явной контрактной семантикой:
  True  — пользователь состоит в таблице;
  False — не состоит;
  None  — сбой БД (отличается от «не состоит», чтобы вызывающий код мог
         ответить «обратитесь в поддержку», а не молчать).
"""
from config import PATH_TO_DB_USERS
from sqlite3 import connect
import logging


def _user_has_role(id, table: str):
    if id is None:
        return False
    try:
        with connect(PATH_TO_DB_USERS) as db:
            cursor = db.cursor()
            # имя таблицы — константа модуля ('student'/'teacher'), не ввод юзера
            cursor.execute(f"SELECT 1 FROM {table} WHERE id = ?", (int(id),))
            return cursor.fetchone() is not None
    except Exception as e:
        logging.error(f"Произошла ошибка в функции is_{table}: {e}")
        return None


def is_student(id=None):
    """Есть ли пользователь в таблице student. True/False, None — сбой БД."""
    return _user_has_role(id, 'student')


def is_teacher(id=None):
    """Есть ли пользователь в таблице teacher. True/False, None — сбой БД."""
    return _user_has_role(id, 'teacher')
