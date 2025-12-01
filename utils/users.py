from sqlite3 import connect, Row

from config import PATH_TO_DB_USERS, PATH_TO_DB_TASK


class Teacher():
    def get_statistics(self, id: int):
        try:
            with connect(PATH_TO_DB_USERS) as db:
                db.row_factory = Row
                cursor = db.cursor()
                cursor.execute("SELECT id, name FROM student WHERE id_teacher = ?", (id,))
                self.students_info = cursor.fetchall()
                cursor.execute("SELECT name FROM teacher WHERE id = ?", (id,))
                self.name_teacher = cursor.fetchone()
        except Exception as e:
            print(f"Ошибка при выполнении функции get_statistics: {e}")

class Student():
    def get_statistics(self, id: int):
        try:
            with connect(PATH_TO_DB_USERS) as db:
                db.row_factory = Row
                cursor = db.cursor()
                cursor.execute("SELECT name FROM student WHERE id = ?", (id,))
                self.name_student = cursor.fetchone()
        except Exception as e:
            print(f"Ошибка при выполнении функции get_statistics: {e}")

    def get_students_tasks(self, id: int):
        try:
            with connect(PATH_TO_DB_TASK) as db:
                db.row_factory = Row
                cursor = db.cursor()
                cursor.execute("SELECT id, id_teacher, id_student, text, file_name, file_type, file_data, deadline, is_active, answer_text, answer_file_name, answer_file_type, answer_file_data, marks FROM task WHERE id_student = ?", (id,))
                self.homework_active = cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при выполнении функции get_students_tasks: {e}")