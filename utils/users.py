from sqlite3 import connect, Row

from config import PATH_TO_DB_USERS


class Teacher():
    def get_statistics(self, id: int):
        try:
            with connect(PATH_TO_DB_USERS) as db:
                db.row_factory = Row
                cursor = db.cursor()
                cursor.execute("SELECT id FROM student WHERE id_teacher = ?", (id,))
                self.students_id = cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при выполнении функции get_statistics: {e}")
