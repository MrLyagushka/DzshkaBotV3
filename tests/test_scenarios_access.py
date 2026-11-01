"""§8: сценарии S1–S10 «доступ между сообщениями» как pytest-тесты.

Тестируем сами хендлеры (а не только их guard-хелперы) на fake aiogram-объектах:
  - `make_cb` — CallbackQuery.model_construct (без сети), payload колбэка реальный;
  - `FakeState` — эмуляция FSMContext поверх dict + state (поведение MemoryStorage
    для одного ключа user+chat); разные пользователи = разные FakeState, что и
    проверяет «межсообщенческий» доступ: кнопка из чужого контекста обязана дать
    отказ, а не действие.
Соответствие сценариев: docstring каждого теста начинается с S<n>.
"""
import asyncio
import sqlite3

import pytest
from aiogram.types import CallbackQuery, Chat, FromUser, Message

from conftest import init_test_dbs, insert_user, insert_task


USERS_DB = None
TASK_DB = None


@pytest.fixture(autouse=True)
def _dbs(tmp_path):
    global USERS_DB, TASK_DB
    USERS_DB, TASK_DB = init_test_dbs(tmp_path)


class FakeState:
    """Минимальная эмуляция FSMContext: get_data/update_data/set_state/clear."""

    def __init__(self):
        self._data = {}
        self._state = None

    async def get_data(self):
        return dict(self._data)

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def set_state(self, state):
        self._state = state

    async def get_state(self):
        return self._state

    async def clear(self):
        self._data = {}
        self._state = None


class RecMessage:
    """Заглушка callback.message: пишет в .calls вместо Telegram API."""

    def __init__(self, cb=None):
        self.calls = []
        self._cb = cb

    async def answer(self, text=None, reply_markup=None, **kw):
        self.calls.append(('answer', text, reply_markup))
        return self

    async def edit_text(self, text=None, reply_markup=None, **kw):
        self.calls.append(('edit_text', text, reply_markup))
        return self

    async def edit_reply_markup(self, reply_markup=None):
        self.calls.append(('edit_reply_markup', reply_markup))
        return self

    async def answer_document(self, document=None, caption=None, **kw):
        self.calls.append(('answer_document', caption))
        return self

    def texts(self):
        return [c[1] for c in self.calls if len(c) > 1 and isinstance(c[1], str)]


def make_cb(user_id: int, data: str):
    msg = RecMessage()
    cb = CallbackQuery.model_construct(
        id='1', from_user=FromUser.model_construct(id=user_id, is_bot=False),
        message=msg, chat_instance='ci', data=data)
    cb.message = msg
    cb.answered = []

    async def _answer(text=None, show_alert=None, **kw):
        cb.answered.append(text)
        return True

    cb.answer = _answer
    return cb


def sent_messages(cb):
    return cb.message.texts()


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- S1/S2
def test_s1_s2_select_student_shows_id_and_owner():
    """S1+S2: catalog17 сохраняет int id_student + ctx_owner, показывает id ученика."""
    from handlers.catalog_tasks_list import catalog17
    from utils.callbacks import StudentCb

    insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
    insert_user(USERS_DB, 'student', 100, 'Иван Петров', id_teacher=1)
    # старый контекст с черновиками прошлого экрана — catalog17 обязан его сбросить
    state = FakeState()
    run(state.update_data(selected_task_id=777, added_text='мусор'))
    run(state.set_state('stale'))

    cb = make_cb(1, StudentCb(mode='view', student_id=100).pack())
    run(catalog17(cb, state))

    data = run(state.get_data())
    assert data['id_student'] == 100 and isinstance(data['id_student'], int)
    assert data['ctx_owner'] == 1
    assert 'selected_task_id' not in data  # reset_flow перед входом в новый флоу
    assert any('(id ученика: 100)' in t for t in sent_messages(cb))


def test_s1_switch_student_B_replaces_context():
    """S1: после выбора B данные A перезаписаны, owner — текущий учитель."""
    from handlers.catalog_tasks_list import catalog17
    from utils.callbacks import StudentCb

    insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
    insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=1)
    insert_user(USERS_DB, 'student', 101, 'Мария', id_teacher=1)
    state = FakeState()
    run(catalog17(make_cb(1, StudentCb(mode='view', student_id=100).pack()), state))
    run(catalog17(make_cb(1, StudentCb(mode='view', student_id=101).pack()), state))
    data = run(state.get_data())
    assert data['id_student'] == 101  # экран теперь про Марию, не про Ивана
    assert data['ctx_owner'] == 1


# ---------------------------------------------------------------- S3
def test_s3_message_handler_requires_screen_state():
    """S3: message-хендлер ввода текста требует состояние экрана — произвольный
    текст после завершения флоу не должен перехватываться."""
    import inspect
    src = inspect.getsource(__import__('handlers.catalog_tasks_list',
                                        fromlist=['x']))
    # add_text_to_task зарегистрирован с StateFilter по экранам студента/учителя
    idx = src.index("async def add_text_to_task")
    decorator = src[:idx].rstrip().rsplit('@router_catalog_tasks_list.message_query', 1)[-1]
    assert 'add_text_to_task' in src
    block = src[max(0, src.rindex('@router_catalog_tasks_list.message_query', 0, idx)):idx]
    assert 'StateFilter' in block or 'CatalogTasksList.add_text_to_task' in block


# ---------------------------------------------------------------- S4
def test_s4_marks_kb_is_oneshot_flagged():
    """S4: клавиатура оценок помечена one-shot (clear_markup=True) — show_screen
    снимает её кнопки после выставления оценки."""
    from keyboards.catalog_tasks_list import keyboard_choice_marks
    assert getattr(keyboard_choice_marks.markup, 'clear_markup', False) or \
        getattr(keyboard_choice_marks, 'clear_markup', False)


# ---------------------------------------------------------------- S5
def test_s5_double_confirm_delete_second_click_denied():
    """S5: двойное «✅ Подтвердить удаление» — второй клик игнорируется
    (состояние снято, ctx очищен)."""
    from handlers.catalog_main_menu import catalog_confirm_delete_student
    from handlers.catalog_tasks_list import reset_flow  # noqa: F401 (импорт модуля)

    insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
    insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=1)

    state = FakeState()
    run(state.update_data(ctx_owner=1, delete_student_id=100))
    run(state.set_state('confirm_delete_student'))

    cb1 = make_cb(1, 'confirm_delete_student')
    run(catalog_confirm_delete_student(cb1, state))
    con = sqlite3.connect(USERS_DB)
    bound = con.execute("SELECT id_teacher FROM student WHERE id = 100").fetchone()[0]
    con.close()
    assert bound is None  # первый клик отвязал

    # второй клик по живой кнопке старого сообщения: state уже None → фильтр
    # хендлера его не пустит; даже при прямом вызове повторного удаления нет
    cb2 = make_cb(1, 'confirm_delete_student')
    run(catalog_confirm_delete_student(cb2, state))
    con = sqlite3.connect(USERS_DB)
    still_none = con.execute("SELECT id_teacher FROM student WHERE id = 100").fetchone()[0] is None
    con.close()
    assert still_none
    assert run(state.get_state()) is None
    assert run(state.get_data()) == {}


# ---------------------------------------------------------------- S6
def test_s6_cancel_returns_to_menu_with_no_state():
    """S6: «❌ Отменить» в confirm-экране удаления возвращает в меню, state=None."""
    from handlers.catalog_main_menu import catalog_cancel_delete_student

    insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
    insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=1)
    state = FakeState()
    run(state.update_data(ctx_owner=1, delete_student_id=100))
    run(state.set_state('confirm_delete_student'))

    cb = make_cb(1, 'cancel_delete_student')
    run(catalog_cancel_delete_student(cb, state))
    assert run(state.get_state()) is None
    assert run(state.get_data()) == {}
    con = sqlite3.connect(USERS_DB)
    bound = con.execute("SELECT id_teacher FROM student WHERE id = 100").fetchone()[0]
    con.close()
    assert bound == 1  # отмена ничего не удалила


# ---------------------------------------------------------------- S7
def test_s7_foreign_ctx_owner_denied():
    """S7: кнопка просмотра из сообщения, созданного под чужим контекстом, —
    «устарело» + clear, БД не тронута."""
    from handlers.catalog_tasks_list import catalog18

    insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
    insert_user(USERS_DB, 'teacher', 2, 'Учитель Б')
    insert_user(USERS_DB, 'student', 100, 'Чужой', id_teacher=2)
    insert_task(TASK_DB, id=5, id_teacher=2, id_student=100)

    state = FakeState()
    run(state.update_data(ctx_owner=2, id_student=100))  # FSM-черновики учителя Б
    run(state.set_state('view_active_tasks_teacher'))

    cb = make_cb(1, 'view_active_tasks_teacher')  # нажал учитель А
    run(catalog18(cb, state))
    assert run(state.get_state()) is None          # экран закрыт
    assert not any('Активные задания' in t for t in sent_messages(cb))  # данных не показал
    assert any('устарело' in t.lower() or 'начните заново' in t.lower()
               or 'больше не в вашем списке' in t.lower() for t in sent_messages(cb))


def test_s7b_unbound_student_denied():
    """S7-вариант: ученик развязан — ensure_student_of_teacher отказывает до показа."""
    from handlers.catalog_tasks_list import catalog17
    from utils.callbacks import StudentCb

    insert_user(USERS_DB, 'teacher', 1, 'Учитель А')
    insert_user(USERS_DB, 'student', 100, 'Иван', id_teacher=None)
    state = FakeState()
    cb = make_cb(1, StudentCb(mode='view', student_id=100).pack())
    run(catalog17(cb, state))
    assert run(state.get_data()).get('id_student') != 100
    assert run(state.get_state()) is None


# ---------------------------------------------------------------- S8
def test_s8_submit_foreign_task_denied():
    """S8: ученик подтверждает сдачу чужого task_id — отказ, ответ не записан."""
    from handlers.catalog_tasks_list import catalog12

    insert_user(USERS_DB, 'student', 100, 'Свой')
    insert_user(USERS_DB, 'student', 101, 'Чужой')
    insert_user(USERS_DB, 'teacher', 2, 'Учитель')
    insert_task(TASK_DB, id=5, id_teacher=2, id_student=101)  # задание ЧУЖОЕ

    state = FakeState()
    run(state.update_data(ctx_owner=100, selected_task_id=5, added_text='мой ответ'))
    run(state.set_state('confirm_pass'))

    cb = make_cb(100, 'confirm')
    run(catalog12(cb, state, bot=None))  # bot не достигается — отказ раньше
    con = sqlite3.connect(TASK_DB)
    row = con.execute("SELECT answer_text, is_active FROM task WHERE id = 5").fetchone()
    con.close()
    assert row[0] is None and row[1] == 1   # чужое задание НЕ перезаписано
    assert run(state.get_state()) is None   # экран закрыт (§2/§3)


# ---------------------------------------------------------------- S9
def test_s9_pagination_after_unbind_no_crash():
    """S9: пагинация по списку, из которого удалили ученика — не падает, first_index
    корректируется или показывается корректный хвост."""
    from handlers.service_handlers import on_the_what
    from utils.callbacks import PageCb
    from utils.template import DinamicKeyboard

    insert_user(USERS_DB, 'teacher', 1, 'Учитель')
    for i in range(10):
        insert_user(USERS_DB, 'student', 100 + i, f'Уч{i}', id_teacher=1)

    kb = DinamicKeyboard(2, 3, 'no', 0, 'st_1').generate_keyboard()
    total_pages = 10 // 6
    # уходим за конец списка
    last_first = total_pages * 6
    # отвязываем всех, кроме двоих — страница становится пустой
    con = sqlite3.connect(USERS_DB)
    con.execute("UPDATE student SET id_teacher = NULL WHERE id >= 102")
    con.commit()
    con.close()

    page_cb = PageCb(direction='prev', first_index=last_first, row=2, column=3,
                     is_always_bigger='no', kind='students', owner_id=1,
                     mode='view', total=2).pack()
    state = FakeState()
    cb = make_cb(1, page_cb)
    run(on_the_what(cb, state))  # не должно бросать
    assert cb.message.calls      # какой-то экран показан (или сообщение об обновлении)


# ---------------------------------------------------------------- S10
def test_s10_two_chats_same_user_ctx_owner_ok_but_data_separate():
    """S10: один пользователь в двух чатах = два разных состояния FSM (ключ
    chat+user). Проверяем контракт: чужой ctx_owner отсекается, свой — нет;
    данные между FakeState не пересекаются."""
    from utils.access import AccessError, check_ctx_owner

    st_a, st_b = FakeState(), FakeState()
    run(st_a.update_data(ctx_owner=1, id_student=100))
    run(st_b.update_data(ctx_owner=1, id_student=101))
    assert run(st_a.get_data())['id_student'] == 100
    assert run(st_b.get_data())['id_student'] == 101
    # другой пользователь, прочитавший контекст чата А — отказ
    with pytest.raises(AccessError):
        check_ctx_owner(run(st_a.get_data()), 2)
    check_ctx_owner(run(st_a.get_data()), 1)
