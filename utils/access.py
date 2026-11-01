"""Центральные проверки доступа между сообщениями (см. REFACTORING_GUIDE.md, §3).

Проблема: FSM-данные (`id_student`, `selected_task_id`) хранятся в MemoryStorage и
переживают переходы между экранами; кнопки старых inline-сообщений остаются живыми.
Хендлер, который читает `state.get_data()` без сверки с `callback.from_user.id`,
может показать/изменить данные чужого ученика или чужого задания.

Правило (§3): каждый хендлер, использующий id из FSM, обязан:
  a) проверить владельца FSM-контекста (`ctx_owner` == from_user.id);
  b) получить строку задачи из БД и сверить `task.id_student` / `task.id_teacher`;
  c) при несовпадении — ответить «Сообщение устарело…», сделать `state.clear()` и НЕ писать в БД.

Здесь нет aiogram-зависимостей на уровне импорта типов сообщений — только БД и исключения,
поэтому модуль можно переиспользовать и в тестах.
"""
import logging

from utils.users import Student, Teacher


class AccessError(Exception):
    """Отказ в доступе: данные сообщения относятся к другому пользователю/экрану."""

    def __init__(self, message: str = 'Сообщение устарело, начните заново'):
        super().__init__(message)
        self.user_message = message


def check_ctx_owner(data: dict, user_id: int) -> None:
    """FSM-черновики принадлежат тому, кто их записал (§3.2).

    Ключ FSM = chat+user, но один пользователь может быть в нескольких чатах, а
    старые записи MemoryStorage могут «дожить» до нового флоу. Если ctx_owner не
    совпадает — данные считаются чужими.
    """
    owner = data.get('ctx_owner')
    if owner is not None and int(owner) != int(user_id):
        raise AccessError()


def get_task_row(task_id: int) -> dict:
    """Строка задачи из БД по id. AccessError, если задача удалена/некорректный id."""
    try:
        task_id = int(task_id)
    except (TypeError, ValueError):
        raise AccessError()
    row = Student().get_task_by_id(task_id)
    if row is None:
        raise AccessError('Задание не найдено, начните заново')
    return row


def ensure_task_for_student(task_row: dict, student_id: int) -> dict:
    """Задача принадлежит именно этому ученику (§3, кейс catalog12)."""
    if task_row.get('id_student') is None or int(task_row['id_student']) != int(student_id):
        raise AccessError()
    return task_row


def ensure_task_for_teacher(task_row: dict, teacher_id: int) -> dict:
    """Задача ведёт именно этот учитель (§3, кейсы catalog24/26/35/37)."""
    if task_row.get('id_teacher') is None or int(task_row['id_teacher']) != int(teacher_id):
        raise AccessError()
    return task_row


def ensure_student_of_teacher(student_id: int, teacher_id: int) -> None:
    """Ученик состоит именно у этого учителя (§3, кейсы catalog17/18/20/30, delete-student)."""
    teacher = Teacher()
    if not teacher.is_student_of_teacher(int(student_id), int(teacher_id)):
        raise AccessError('Этот ученик больше не в вашем списке, начните заново')


async def stale_session(callback, state) -> None:
    """Единая реакция на отказ доступа: ответ + обязательный сброс экрана (§2/§3)."""
    try:
        await callback.answer('⛔Нет доступа')
    except Exception as e:  # answer уже может быть отправлен — не роняем хендлер
        logging.debug(f'stale_session: callback.answer пропущен: {e}')
    await callback.message.answer(
        'Сообщение устарело, начните заново',
    )
    await state.clear()
