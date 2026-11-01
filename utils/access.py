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


def ctx_owner_field(user_id: int) -> dict:
    """Значение для state.update_data(..., **ctx_owner_field(id)) — единый способ
    пометить FSM-черновики владельцем (§3.2)."""
    return {'ctx_owner': int(user_id)}


async def ensure_student_exists(student_id: int) -> None:
    """Ученик существует в БД (для add_student; §3.3)."""
    student = Student()
    student.get_statistics(int(student_id))
    if not getattr(student, 'name_student', None):
        raise AccessError('Ученик с таким ID не найден')


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


async def retire_keyboard(message) -> None:
    """Снять кнопки с текущего сообщения (one-shot для confirm-экранов, §4).

    Терминальные шаги («✅ Подтвердить» → действие выполнено) обязаны «гасить»
    свою клавиатуру: иначе живой кнопкой из старого сообщения можно повторить
    действие или подтвердить чужой экран. Кнопки, ведущие к следующему шагу
    (например «❌ Отменить»), не снимаются — см. clear_markup=... в
    keyboards/catalog_tasks_list.py.
    """
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        # «message is not modified» / сообщение удалено — не критично
        logging.debug(f'retire_keyboard: edit_reply_markup пропущен: {e}')


def _is_confirm_kb(markup) -> bool:
    return bool(getattr(markup, 'clear_markup', False))


async def show_screen(callback, text: str = None, reply_markup=None,
                      document=None, caption: str = ''):
    """Показать экран (§4): редактировать своё сообщение вместо answer().

    Колбэк-хендлеры отвечают через callback.message.answer(...) — в чате
    накапливаются старые сообщения с живыми кнопками, по которым можно
    повторить терминальное действие или перехватить чужой экран. Здесь:
      - текст экрана ставится edit_text на сообщении, с которого нажали кнопку;
      - если предыдущий экран был one-shot-подтверждением (clear_markup=True),
        его кнопки снимаются до показа нового сообщения;
      - edit_text недоступен (сообщение слишком старое/удалено) — откат к
        обычному answer(), чтобы не ронять хендлер.
    Возвращает отправленное/отредактированное сообщение.
    """
    if reply_markup is not None and _is_confirm_kb(reply_markup):
        await retire_keyboard(callback.message)
    if document is not None:
        await callback.message.answer_document(document=document, caption=caption)
    msg = None
    if text is not None:
        try:
            msg = await callback.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logging.debug(f'show_screen: edit_text не удался ({e}), отвечаю новым сообщением')
            msg = await callback.message.answer(text, reply_markup=reply_markup)
    elif reply_markup is not None:
        try:
            msg = await callback.message.edit_reply_markup(reply_markup=reply_markup)
        except Exception as e:
            logging.debug(f'show_screen: edit_reply_markup не удался ({e})')
    return msg
