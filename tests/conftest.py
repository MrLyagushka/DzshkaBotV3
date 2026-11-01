"""Инфраструктура pytest (см. REFACTORING_GUIDE.md, §7/§8).

Критично: config.py подменяется ДО импорта utils.* — иначе модули БД
захардкодят пути к рабочим базам db/users.db / db/task.db. Каждый тестовый
модуль вызывает init_test_dbs(tmp_path) в фикстуре с autouse=True.

Механизм перезагрузки (исправлено в §9): init_test_dbs создаёт файлы баз и
перезагружает ВСЕ модули, которые захватили константы PATH_TO_DB_* на уровне
импорта (utils.*, handlers.*, keyboards.*) — поэтому повторные вызовы с новым
tmp_path не пишут в базу первого теста. Модули, НЕ читающие config при импорте
(utils.access, utils.callbacks), перезагружать не нужно.
"""
import os
import sys
import sqlite3
import types
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('BOT_TOKEN', '123456:TEST')

USERS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS "users" ("id" INTEGER, "username" TEXT);
    CREATE TABLE IF NOT EXISTS "student" ("id" INTEGER, "username" TEXT,
        "name" TEXT, "id_teacher" INTEGER);
    CREATE TABLE IF NOT EXISTS "teacher" ("id" INTEGER, "username" TEXT, "name" TEXT);
"""

TASK_SCHEMA = """
    CREATE TABLE IF NOT EXISTS "task" (
        "id" INTEGER, "id_teacher" INTEGER, "id_student" INTEGER,
        "deadline" TEXT, "marks" INTEGER, "is_active" INTEGER,
        "text" TEXT, "file_name" TEXT, "file_type" TEXT, "file_data" BLOB,
        "answer_text" TEXT, "answer_file_name" TEXT,
        "answer_file_type" TEXT, "answer_file_data" BLOB);
    CREATE TABLE IF NOT EXISTS "tutorial" ("text" TEXT);
"""


def _make_fake_config(users_db: str, task_db: str) -> types.ModuleType:
    fake_config = types.ModuleType('config')
    fake_config.BOT_TOKEN = os.environ['BOT_TOKEN']
    fake_config.ADMIN_ID = '1'
    fake_config.PATH_TO_DB_USERS = users_db
    fake_config.PATH_TO_DB_TASK = task_db
    return fake_config


def _reload_dependents():
    """Сбрасываем из sys.modules всё, что захватило config-константы при импорте."""
    for name in list(sys.modules):
        if name == 'config' or name.startswith('utils.') or name.startswith('handlers.') \
                or name.startswith('keyboards.'):
            del sys.modules[name]


def init_test_dbs(tmp_path):
    """Создаёт временные users.db/task.db (схема как в install.sh) и перепривязывает
    config.PATH_TO_DB_* + перезагружает utils/handlers/keyboards — до/после импорта."""
    tmp_dir = str(tmp_path)
    os.makedirs(tmp_dir, exist_ok=True)  # подстраховка: файл должен открываться всегда
    users_db = os.path.join(tmp_dir, 'users.db')
    task_db = os.path.join(tmp_dir, 'task.db')

    con = sqlite3.connect(users_db)
    con.executescript(USERS_SCHEMA)
    con.commit()
    con.close()

    con = sqlite3.connect(task_db)
    con.executescript(TASK_SCHEMA)
    con.commit()
    con.close()

    sys.modules['config'] = _make_fake_config(users_db, task_db)
    _reload_dependents()

    return users_db, task_db


# --- совместимость со старым импортом из conftest -------------------------
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
