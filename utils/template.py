from typing import List, Optional
from aiogram.filters.callback_data import CallbackData

from typing_extensions import Literal, TypedDict
from utils.users import Teacher, Student
from utils.menu import Menu
from utils.callbacks import (
    PageCb,
    StudentCb,
    TaskCb,
    student_button_text,
    task_button_text,
)


# Старые сокращения режимов -> новые типизированные контракты (см. utils/callbacks.py)
_STUDENT_KINDS = {'st': 'view',   # список учеников учителя: выбор ученика
                  'ds': 'del'}    # список учеников учителя: выбор ученика для отвязки/удаления
_TASK_KINDS = {'tsa': 'a',        # активные задания
               'tsd': 'd',        # завершенные (сданные) задания
               'tsp': 'p'}        # задания на проверке
_IS_ACTIVE_BY_MODE = {'a': 1, 'd': 0, 'p': -1}
_REVERSE_BY_MODE = {'a': True, 'd': False, 'p': True}


def parse_button_info(button_info: str):
    """Разбирает 'st_<id>' / 'ds_<id>' / 'tsa_<id>' -> (kind, owner_id, mode).

    Разделитель '_' здесь встречается ровно один раз (id — число), поэтому split безопасен.
    """
    kind, _, raw_id = button_info.partition('_')
    if kind in _STUDENT_KINDS:
        return 'students', int(raw_id), _STUDENT_KINDS[kind]
    if kind in _TASK_KINDS:
        return 'tasks', int(raw_id), _TASK_KINDS[kind]
    raise ValueError(f'Неизвестный формат button_info: {button_info!r}')


def load_buttons(kind: str, owner_id: int, mode: str):
    """Возвращает (texts, ids) — подписи кнопок и их id из БД."""
    if kind == 'students':
        data = Teacher()
        data.get_statistics(owner_id)
        return ([student_button_text(x['name'], x['id']) for x in data.students_info],
                [x['id'] for x in data.students_info])
    data = Student()
    data.get_students_tasks(owner_id, reverse=_REVERSE_BY_MODE[mode])
    wanted = _IS_ACTIVE_BY_MODE[mode]
    tasks = [x for x in data.homework_active if x['is_active'] == wanted]
    return ([task_button_text(x['deadline']) for x in tasks], [x['id'] for x in tasks])


class DinamicKeyboard():

    def __init__(self, row, column, is_always_bigger_column_multiply_row: Literal['yes', 'no'], first_index,
                 button_info: str):
        """
        Кароч, указываешь количество строк - row, столбцов - column. Также введи, будет ли твоя клавиатура
        всегда больше чем column*row или нет. И еще список кнопок.
        Формат button_info: st, ds, tsa, tsd, tsp. Список учеников, список учеников для удаления,
        список заданий у ученика (активных / сданных / на проверке).
        st_idteacher, ds_idteacher или tsa_idstudent и т.д.
        Подписи кнопок и callback_data разделены: в callback_data только типизированный контракт
        (StudentCb/TaskCb/PageCb), имя ученика или дата туда не попадают.
        """
        self.first_index = first_index
        self.row = row
        self.column = column
        self.is_always_bigger_column_multiply_row = is_always_bigger_column_multiply_row
        self.button_info = button_info

    def _page_callback(self, direction: str, total: int) -> str:
        kind, owner_id, mode = parse_button_info(self.button_info)
        return PageCb(direction=direction,
                      first_index=self.first_index,
                      row=self.row,
                      column=self.column,
                      is_always_bigger=self.is_always_bigger_column_multiply_row,
                      kind=kind,
                      owner_id=owner_id,
                      mode=mode,
                      total=total).pack()

    def generate_keyboard(self):
        """Собирает inline-клавиатуру списка: кнопки элементов + пагинация."""
        dinamic_keyboard = Menu('inline', self.row+1)
        kind, owner_id, mode = parse_button_info(self.button_info)
        self.button_list, self.button_list2 = load_buttons(kind, owner_id, mode)
        count = 0
        while count < self.row * self.column and self.first_index + count < len(self.button_list):
            row = count // self.column
            item_id = self.button_list2[self.first_index+count]
            if kind == 'students':
                callback_data = StudentCb(mode=mode, student_id=item_id).pack()
            else:
                callback_data = TaskCb(mode=mode, task_id=item_id).pack()
            dinamic_keyboard.new_button(row_number=row+1, text=self.button_list[self.first_index+count],
                                        # Т.к. в классе Menu, row_number идет от 0, для удобства пользования
                                        callback_data=callback_data)
            count += 1
        if len(self.button_list) > self.row*self.column:
            dinamic_keyboard.new_button(row_number=self.row+1, text='<',  # Т.к. в классе Menu, row_number идет от 0, для удобства пользования
                                        callback_data=self._page_callback('prev', len(self.button_list)))
            dinamic_keyboard.new_button(row_number=self.row+1, text='>',
                                        callback_data=self._page_callback('next', len(self.button_list)))
        return dinamic_keyboard.markup