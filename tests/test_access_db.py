"""§3/§5: guard-хелперы utils/access.py и контракты БД utils/catalog.py.

Соответствуют ручным сценариям §8: S7 (чужой ученик), S8 (чужое задание),
плюс атомарность add/remove_student и статусные контракты ('ok'/
'not_found'/'error') из §5.
"""
import pytest

from conftest import init_test_dbs, insert_user, insert_task  # noqa: F401


USERS_DB = None
TASK_DB = None


@pytest.fixture(autouse=True)
def _dbs(tmp_path):
    global USERS_DB, TASK_DB
    USERS_DB, TASK_DB = init_test_dbs(tmp_path)


def _student_teacher_id():
    """id_teacher у ученика 100 — напрямую из БД."""
    import sqlite3
    con = sqlite3.connect(USERS_DB)
    row = con.execute("SELECT id_teacher FROM student WHERE id = 100").fetchone()
    con.close()
    return row[0] if row else None


class TestAccessGuards:
    def test_check_ctx_owner_denies_foreign(self):
        from utils.access import AccessError, check_ctx_owner
        with pytest.raises(AccessError):
            check_ctx_owner({'ctx_owner': 999}, user_id=1)
        check_ctx_owner({'ctx_owner': 1}, user_id=1)  # не бросает
        check_ctx_owner({}, user_id=1)  # ctx_owner ещё не записан — не блокируем

    def test_ensure_student_of_teacher_s7(self):
        """S7: ученик X НЕ состоит у учителя A — отказ (а не показ данных X)."""
        from utils.access import AccessError, ensure_student_of_teacher
        insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=2)
        insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
        ensure_student_of_teacher(100, 2)  # свой — ок
        with pytest.raises(AccessError):
            ensure_student_of_teacher(100, 1)  # чужой ученик — отказ
        with pytest.raises(AccessError):
            ensure_student_of_teacher(999, 2)  # несуществующий — отказ

    def test_ensure_task_for_student_s8(self):
        """S8: task принадлежит другому ученику — отказ."""
        from utils.access import AccessError, ensure_task_for_student, get_task_row
        insert_task(TASK_DB, id=5, id_teacher=2, id_student=100)
        row = get_task_row(5)
        ensure_task_for_student(row, 100)
        with pytest.raises(AccessError):
            ensure_task_for_student(row, 101)

    def test_ensure_task_for_teacher(self):
        from utils.access import AccessError, ensure_task_for_teacher, get_task_row
        insert_task(TASK_DB, id=6, id_teacher=2, id_student=100)
        row = get_task_row(6)
        ensure_task_for_teacher(row, 2)
        with pytest.raises(AccessError):
            ensure_task_for_teacher(row, 1)

    def test_get_task_row_missing(self):
        from utils.access import AccessError, get_task_row
        with pytest.raises(AccessError):
            get_task_row(4242)
        with pytest.raises(AccessError):
            get_task_row('abc')  # некорректный id тоже отказ, а не падение


class TestCatalogContracts:
    def test_add_student_rejects_taken(self):
        from utils.catalog import add_student
        insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=None)
        assert add_student(100, 2) == 'ok'
        assert _student_teacher_id() == 2
        # §3.3: перехват чужого ученика запрещён
        assert add_student(100, 3) == 'busy_other_teacher'
        assert _student_teacher_id() == 2
        assert add_student(100, 2) == 'already_mine'
        assert add_student(999, 2) == 'not_found'

    def test_remove_student_wrong_teacher(self):
        from utils.catalog import remove_student
        insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=2)
        assert remove_student(100, 1) == 'not_found'  # чужой не отвяжется
        assert _student_teacher_id() == 2
        assert remove_student(100, 2) == 'ok'
        assert _student_teacher_id() is None
        assert remove_student(100, 2) == 'not_found'  # повторный клик — not_found

    def test_save_answer_task_owner_in_where(self):
        """S8 на уровне SQL: даже если хендлер обошёл, чужая запись не обновится."""
        from utils.catalog import save_answer_task
        insert_task(TASK_DB, id=5, id_teacher=2, id_student=100)
        assert save_answer_task(5, 'ответ', None, None, None, id_student=101) == 'not_found'
        assert save_answer_task(5, 'ответ', None, None, None, id_student=100) == 'ok'
        import sqlite3
        con = sqlite3.connect(TASK_DB)
        row = con.execute("SELECT answer_text, is_active FROM task WHERE id = 5").fetchone()
        con.close()
        assert row == ('ответ', -1)  # сдано: is_active=-1
        assert save_answer_task(4242, 'x', None, None, None, id_student=100) == 'not_found'

    def test_set_marks_requires_owner(self):
        from utils.catalog import set_marks
        insert_task(TASK_DB, id=5, id_teacher=2, id_student=100)
        assert set_marks(5, 5, id_teacher=1) is False  # чужой учитель
        assert set_marks(5, 5, id_teacher=2) is True
        import sqlite3
        con = sqlite3.connect(TASK_DB)
        marks = con.execute("SELECT marks FROM task WHERE id = 5").fetchone()[0]
        con.close()
        assert marks == 5

    def test_set_pass_status_contract(self):
        from utils.catalog import set_pass
        insert_task(TASK_DB, id=5, id_teacher=2, id_student=100, is_active=-1)
        res = set_pass(5, id_teacher=1)
        assert res['status'] == 'not_found' and res['task'] is None
        res = set_pass(5, id_teacher=2)
        assert res['status'] == 'ok'
        assert res['task']['is_active'] == 0
        assert set_pass(4242, id_teacher=2)['status'] == 'not_found'

    def test_update_deadline_and_return_goback_owner(self):
        from utils.catalog import update_deadline, return_goback
        insert_task(TASK_DB, id=5, id_teacher=2, id_student=100)
        assert update_deadline(5, '09.11.2026', id_teacher=1) is False
        assert update_deadline(5, '09.11.2026', id_teacher=2) is True
        assert return_goback(5, id_teacher=1) is False
        assert return_goback(5, id_teacher=2) is True
        import sqlite3
        con = sqlite3.connect(TASK_DB)
        row = con.execute("SELECT deadline, is_active FROM task WHERE id = 5").fetchone()
        con.close()
        assert row == ('09.11.2026', 1)  # возвращено на дорешку


class TestRolesOptimized:
    """§5.6: is_student/is_teacher(id) — SELECT 1, контракт True/False/None."""

    def test_roles_point_query(self):
        from utils.filter import is_student, is_teacher
        insert_user(USERS_DB, 'student', 100, 'Иван')
        insert_user(USERS_DB, 'teacher', 2, 'Учитель')
        assert is_student(100) is True
        assert is_student(2) is False       # учитель — не ученик
        assert is_teacher(2) is True
        assert is_teacher(100) is False
        # контракт модуля (см. docstring utils/filter): None-id трактуется как
        # «не состоит» (False), а None возвращается ТОЛЬКО при сбое БД —
        # проверяем на закрытой базе:
        import utils.filter as uf
        broken = uf.PATH_TO_DB_USERS
        uf.PATH_TO_DB_USERS = '/nonexistent_dir/db.sqlite'
        try:
            assert is_student(100) is None and is_teacher(100) is None
        finally:
            uf.PATH_TO_DB_USERS = broken
        assert is_student(None) is False
