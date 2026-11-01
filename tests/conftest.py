"""Инфраструктура pytest (см. REFACTORING_GUIDE.md, §7/§8).

Критично: config.py подменяется ДО импорта utils.* — иначе модули БД
захардкодят пути к рабочим базам db/users.db / db/task.db. Каждый тестовый
модуль вызывает init_test_dbs(tmp_path) в фикстуре с autouse=True.
"""
import os
import sys
import sqlite3
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('BOT_TOKEN', '123456:TEST_TOKEN')


def init_test_dbs(tmp_path):
    """Создаёт временные users.db/task.db (схема как в install.sh) и
    перепривязывает config.PATH_TO_DB_* — до импорта utils.*."""
    users_db = str(tmp_path / 'users.db')
    task_db = str(tmp_path / 'task.db')

    con = sqlite3.connect(users_db)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS "users" ("id" INTEGER, "username" TEXT);
        CREATE TABLE IF NOT EXISTS "student" ("id" INTEGER, "username" TEXT,
            "name" TEXT, "id_teacher" INTEGER);
        CREATE TABLE IF NOT EXISTS "teacher" ("id" INTEGER, "username" TEXT, "name" TEXT);
    """)
    con.commit()
    con.close()

    con = sqlite3.connect(task_db)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS "task" (
            "id" INTEGER, "id_teacher" INTEGER, "id_student" INTEGER,
            "deadline" TEXT, "marks" INTEGER, "is_active" INTEGER,
            "text" TEXT, "file_name" TEXT, "file_type" TEXT, "file_data" BLOB,
            "answer_text" TEXT, "answer_file_name" TEXT,
            "answer_file_type" TEXT, "answer_file_data" BLOB);
        CREATE TABLE IF NOT EXISTS "tutorial" ("text" TEXT);
    """)
    con.commit()
    con.close()

    fake_config = types.ModuleType('config')
    fake_config.BOT_TOKEN = os.environ['BOT_TOKEN']
    fake_config.ADMIN_ID = '1'
    fake_config.PATH_TO_DB_USERS = users_db
    fake_config.PATH_TO_DB_TASK = task_db
    sys.modules['config'] = fake_config

    # ВАЖНО: модули utils.* и handlers.* захватывают PATH_TO_DB_* в момент
    # импорта (`from config import ...`). При повторном вызове init_test_dbs
    # (следующий tmp_path) перезаряжаем ВСЁ, что уже импортировало config, —
    # иначе тесты пишут в базу первого теста.
    for name in list(sys.modules):
        if name == 'config' or name.startswith('utils.') or name.startswith('handlers.') \
                or name.startswith('keyboards.'):
            sys.modules.pop(name, None)

    return users_db, task_db


def insert_user(db_path: str, table: str, id: int, name: str, id_teacher=None):
    con = sqlite3.connect(db_path)
    if table == 'student':
        con.execute("INSERT INTO student (id, username, name, id_teacher) VALUES (?, ?, ?, ?)",
                    (id, f'user{id}', name, id_teacher))
    else:
        con.execute("INSERT INTO teacher (id, username, name) VALUES (?, ?, ?)",
                    (id, f'user{id}', name))
    con.commit()
    con.close()


def insert_task(db_path: str, *, id: int, id_teacher: int, id_student: int,
                deadline: str = '01.11.2026', is_active: int = 1,
                text: str = 'Решить 1+1', marks=None, answer_text=None):
    con = sqlite3.connect(db_path)
    con.execute(
        "INSERT INTO task (id, id_teacher, id_student, deadline, marks, is_active, text,"
        " file_name, file_type, file_data, answer_text, answer_file_name,"
        " answer_file_type, answer_file_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (id, id_teacher, id_student, deadline, marks, is_active, text,
         None, None, None, answer_text, None, None, None))
    con.commit()
    con.close()
