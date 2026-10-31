"""Единые типизированные контракты callback_data (см. REFACTORING_GUIDE.md, §1).

Раньше payload'ы склеивались строками в utils/template.py:
    'callback_data_st_<Имя>_<id>'  и  'callback_datatsa_<дд.мм>_<id>'
Разделитель '_' совпадал с символом внутри имён/дат, поэтому разбор через
split('_')[N] ломался, а префиксы 'st' и 'ds' пересекались в фильтрах
(F.data[:16] == 'callback_data_st' матчил и 'callback_data_ds_...').

Здесь каждый контракт описан классом aiogram CallbackData: сериализация
(pack) и разбор (filter(...)) делаются библиотекой, имена кнопок
в payload не участвуют, id всегда int.

Использование в хендлерах:
    @router.callback_query(StudentCb.filter(mode='del'))
    async def handler(call, callback_data: StudentCb):
        student_id = callback_data.student_id
"""
from typing import Any, Dict, Literal, Optional, Union

from aiogram.filters.callback_data import CallbackData, CallbackQueryFilter
from aiogram.types import CallbackQuery

# Режимы списков учеников: просмотр заданий / отвязка(удаление) из «Список учеников»
StudentMode = Literal['view', 'del']
# Режимы списков заданий: активные / завершенные / на проверке
TaskMode = Literal['a', 'd', 'p']


class _CbModeFilter(CallbackQueryFilter):
    """CallbackQueryFilter + дополнительная проверка поля `mode`."""

    __slots__ = ('callback_data', 'rule', 'expected_mode')

    def __init__(self, *, callback_data, expected_mode: str, rule=None):
        super().__init__(callback_data=callback_data, rule=rule)
        self.expected_mode = expected_mode

    async def __call__(self, query: CallbackQuery) -> Union[Literal[False], Dict[str, Any]]:
        result = await super().__call__(query)
        if result is False:
            return False
        if result['callback_data'].mode != self.expected_mode:
            return False
        return result

    def __str__(self) -> str:
        return self._signature_to_string(
            callback_data=self.callback_data,
            rule=self.rule,
            expected_mode=self.expected_mode,
        )


class StudentCb(CallbackData, prefix='stu'):
    """Кнопка «ученик» в динамическом списке.

    mode='view' — выбрать ученика (просмотр заданий),
    mode='del'  — выбрать ученика для отвязки/удаления (подтверждение).
    """
    mode: StudentMode
    student_id: int

    @classmethod
    def filter(cls, mode: Optional[str] = None, rule=None):  # type: ignore[override]
        if mode is None:
            return super().filter(rule=rule)
        return _CbModeFilter(callback_data=cls, expected_mode=mode, rule=rule)


class TaskCb(CallbackData, prefix='tsk'):
    """Кнопка «задание» в динамическом списке.

    mode='a'  — активные задания,
    mode='d'  — завершенные (сданные) задания,
    mode='p'  — задания на проверке.
    """
    mode: TaskMode
    task_id: int

    @classmethod
    def filter(cls, mode: Optional[str] = None, rule=None):  # type: ignore[override]
        if mode is None:
            return super().filter(rule=rule)
        return _CbModeFilter(callback_data=cls, expected_mode=mode, rule=rule)


class PageCb(CallbackData, prefix='pg'):
    """Пагинация динамического списка ('<' / '>')."""
    direction: Literal['prev', 'next']
    first_index: int
    row: int
    column: int
    kind: Literal['students', 'tasks']
    mode: str  # 'view' | 'del' | TaskMode


def truncate(text: str, limit: int = 20) -> str:
    """Безопасная длина текста кнопки (лимит Telegram — 64 символа, у нас есть префикс)."""
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit - 1] + '…'


def student_button_text(name, student_id: int) -> str:
    """Текст кнопки ученика: «Имя (id)» — id виден учителю сразу при выборе (требование заказчика)."""
    return f'{truncate(name)} ({student_id})'


def task_button_text(deadline) -> str:
    """Текст кнопки задания: дедлайн без года (дд.мм)."""
    return f'До {str(deadline)[5:10]}'
