"""Единые типизированные контракты callback_data (см. REFACTORING_GUIDE.md, §1).

Раньше payload'ы склеивались строками в utils/template.py:
    'callback_data_st_<Имя>_<id>'  и  'callback_datatsa_<дд.мм>_<id>'
Разделитель '_' совпадал с символом внутри имён/дат, поэтому разбор через
split('_')[N] ломался, а префиксы 'st' и 'ds' пересекались в фильтрах
(F.data[:16] == 'callback_data_st' матчил и 'callback_data_ds_...').

Здесь каждый контракт описан классом aiogram CallbackData: сериализация
(pack) и разбор (parse / filter(...)) делаются библиотекой, имена кнопок
в payload не участвуют, id всегда int.
"""
from typing import Literal

from aiogram.filters import BaseFilter, FilterObject
from aiogram.filters.callback_data import CallbackData

# Режимы списков учеников: просмотр заданий / отвязка(удаление) из «Список учеников»
StudentMode = Literal['view', 'del']
# Режимы списков заданий: активные / завершенные / на проверке
TaskMode = Literal['a', 'd', 'p']


class _ModeFilter(BaseFilter):
    """Фильтр по значению поля `mode` у уже распарсенного контракта."""

    def __init__(self, callback_cls, mode: str):
        self.callback_cls = callback_cls
        self.mode = mode

    async def __call__(self, callback_data=None, **kwargs) -> bool:
        if not isinstance(callback_data, self.callback_cls):
            return False
        return callback_data.mode == self.mode


class StudentCb(CallbackData, prefix='stu'):
    """Кнопка «ученик» в динамическом списке.

    mode='view' — выбрать ученика (обработчик catalog17),
    mode='del'  — выбрать ученика для отвязки/удаления (catalog_delete_student_confirm).
    """
    mode: StudentMode
    student_id: int

    @classmethod
    def filter(cls, mode: str | None = None) -> FilterObject:
        base = super().filter()
        if mode is None:
            return base
        base.factory += _ModeFilter(cls, mode)
        return base


class TaskCb(CallbackData, prefix='tsk'):
    """Кнопка «задание» в динамическом списке.

    mode='a'  — активные задания,
    mode='d'  — завершенные (сданные) задания,
    mode='p'  — задания на проверке.
    """
    mode: TaskMode
    task_id: int

    @classmethod
    def filter(cls, mode: str | None = None) -> FilterObject:
        base = super().filter()
        if mode is None:
            return base
        base.factory += _ModeFilter(cls, mode)
        return base


class PageCb(CallbackData, prefix='pg'):
    """Пагинация динамического списка ('<' / '>')."""
    direction: Literal['prev', 'next']
    first_index: int
    row: int
    column: int
    is_always_bigger: Literal['yes', 'no']
    kind: Literal['students', 'tasks']
    owner_id: int
    mode: str  # 'view' | 'del' | TaskMode
    total: int


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
