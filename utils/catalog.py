from sqlite3 import connect, Row
import logging

from config import PATH_TO_DB_TASK, PATH_TO_DB_USERS

def add_student(id_student: int, id_teacher: int) -> str:
    """Привязка ученика к учителю (§3.3).

    Возвращает статус вместо молчаливой записи:
      'ok'                — привязан;
      'not_found'         — ученика с таким id нет;
      'already_mine'      — уже привязан к этому же учителю;
      'busy_other_teacher'— ученик уже закреплён за ДРУГИМ учителем (перехват запрещён);
      'error'             — ошибка БД.
    Запись происходит атомарно: UPDATE ... WHERE id = ? AND (id_teacher IS NULL OR id_teacher = ?),
    поэтому гонка «двое учителей добавили одного ученика» не приведёт к перехвату.
    """
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT id_teacher FROM student WHERE id = ?", (id_student,))
            row = cursor.fetchone()
            if row is None:
                return 'not_found'
            current = row['id_teacher']
            if current is not None and int(current) != int(id_teacher):
                return 'busy_other_teacher'
            if current is not None and int(current) == int(id_teacher):
                return 'already_mine'
            cursor.execute(
                "UPDATE student SET id_teacher = ? WHERE id = ? AND (id_teacher IS NULL OR id_teacher = ?)",
                (id_teacher, id_student, id_teacher),
            )
            db.commit()
            return 'ok' if cursor.rowcount > 0 else 'busy_other_teacher'
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции add_student: {e}")
        return 'error'

def remove_student(id_student: int, id_teacher: int) -> str:
    """Отвязка ученика от учителя (§3.5, унификация контракта — §5).

    Возвращает статус вместо молчаливого True/False:
      'ok'        — ученик отвязан;
      'not_found' — ученик не найден ИЛИ уже привязан к другому учителю
                    (rowcount == 0 у UPDATE ... WHERE id = ? AND id_teacher = ?);
      'error'     — сбой БД (отличается от 'not_found', чтобы хендлер мог
                    ответить «обратитесь в поддержку», а не «уже удалён»).
    """
    try:
        with connect(PATH_TO_DB_USERS) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("UPDATE student SET id_teacher = NULL WHERE id = ? AND id_teacher = ?", (id_student, id_teacher,))
            db.commit()
            return 'ok' if cursor.rowcount > 0 else 'not_found'
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции remove_student: {e}")
        return "error"

def save_answer_task(id_task: int, answer_text: str, answer_file_name: str | None, answer_file_type: str | None, answer_file_data: bytes | None, id_student: int | None = None) -> str:
    """Сохранение ответа ученика (§3.5, унификация контракта — §5).

    `id_student` — ожидаемый владелец задания: попадает в WHERE, поэтому сдача
    чужого задания (кнопкой со старого сообщения) не возможна даже при обходе
    проверок хендлера. Возвращает статус:
      'ok'        — ответ сохранён;
      'not_found' — задание не найдено или принадлежит другому ученику
                    (rowcount == 0);
      'error'     — сбой БД.
    """
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id_student is not None:
                cursor.execute(
                    "UPDATE task SET answer_text = ?, answer_file_name = ?, answer_file_type = ?, answer_file_data = ?, is_active = ? WHERE id = ? AND id_student = ?",
                    (answer_text, answer_file_name, answer_file_type, answer_file_data, -1, id_task, id_student)
                )
            else:
                cursor.execute(
                    "UPDATE task SET answer_text = ?, answer_file_name = ?, answer_file_type = ?, answer_file_data = ?, is_active = ? WHERE id = ?",
                    (answer_text, answer_file_name, answer_file_type, answer_file_data, -1, id_task)
                )
            db.commit()
            return 'ok' if cursor.rowcount > 0 else 'not_found'
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции save_answer_task: {e}")
        return "error"

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
    
def set_pass(id_task: int, id_teacher: int | None = None) -> dict:
    """Отметка «решено» (§3.5, унификация контракта — §5).

    `id_teacher` — ожидаемый владелец задания (в WHERE): чужое задание не отметить.
    Возвращает словарь {'status': ..., 'task': Row|None} вместо списка с
    молчаливыми [], None (чтобы вызывающий код различал причины отказа):
      {'status': 'ok', 'task': <строка>}    — отмечено, строка актуальна;
      {'status': 'not_found', 'task': None} — задание не найдено или
                                              принадлежит другому учителю;
      {'status': 'error', 'task': None}     — сбой БД.
    """
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id_teacher is not None:
                cursor.execute("UPDATE task SET is_active = ? WHERE id = ? AND id_teacher = ?", (0, id_task, id_teacher))
            else:
                cursor.execute("UPDATE task SET is_active = ? WHERE id = ?", (0, id_task,))
            db.commit()
            if cursor.rowcount == 0 and id_teacher is not None:
                return {'status': 'not_found', 'task': None}
            cursor.execute("SELECT id_student, deadline, marks FROM task WHERE id = ?", (id_task,))
            row = cursor.fetchone()
            if row is None:
                return {'status': 'not_found', 'task': None}
            return {'status': 'ok', 'task': row}
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции set_pass: {e}")
        return {'status': 'error', 'task': None}
    
def set_marks(id_task: int, mark: int, id_teacher: int | None = None) -> bool:
    """Выставление оценки (§3.5). `id_teacher` — ожидаемый владелец (в WHERE)."""
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id_teacher is not None:
                cursor.execute("UPDATE task SET marks = ? WHERE id = ? AND id_teacher = ?", (mark, id_task, id_teacher))
            else:
                cursor.execute("UPDATE task SET marks = ? WHERE id = ?", (mark, id_task,))
            db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции set_marks: {e}")
        return False
    
def update_deadline(id_task: int, new_deadline: str, id_teacher: int | None = None) -> bool:
    """Смена дедлайна (§3.5). `id_teacher` — ожидаемый владелец (в WHERE)."""
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id_teacher is not None:
                cursor.execute("UPDATE task SET deadline = ? WHERE id = ? AND id_teacher = ?", (new_deadline, id_task, id_teacher))
            else:
                cursor.execute("UPDATE task SET deadline = ? WHERE id = ?", (new_deadline, id_task,))
            db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции update_deadline: {e}")
        return False
    
def return_goback(id_task: int, id_teacher: int | None = None) -> bool:
    """Возврат задания «на дорешку» (§3.5). `id_teacher` — ожидаемый владелец (в WHERE)."""
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            if id_teacher is not None:
                cursor.execute("UPDATE task SET is_active = ? WHERE id = ? AND id_teacher = ?", (1, id_task, id_teacher))
            else:
                cursor.execute("UPDATE task SET is_active = ? WHERE id = ?", (1, id_task,))
            db.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции return_goback: {e}")
        return False
    
def get_date(id_task: int):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT deadline FROM task WHERE id = ?", (id_task,))
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции get_date: {e}")
        return None
    
def get_is_active(id_task: int):
    try:
        with connect(PATH_TO_DB_TASK) as db:
            db.row_factory = Row
            cursor = db.cursor()
            cursor.execute("SELECT is_active FROM task WHERE id = ?", (id_task,))
            result = cursor.fetchone()
            if result:
                return result['is_active']
            return None
    except Exception as e:
        logging.error(f"Ошибка при выполнении функции get_is_active: {e}")
        return None