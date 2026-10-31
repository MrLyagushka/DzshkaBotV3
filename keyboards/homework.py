from utils.menu import Menu
# Единая общая клавиатура подтверждения «✅ / ❌» (§2): различие экранов — по FSM-состоянию.
from keyboards.catalog_tasks_list import (
    keyboard_catalog_tasks_list_confirm_generic,
    keyboard_time_selection,
)

keyboard_homework = Menu('inline', 3)
keyboard_homework.new_button('Прикрепить файл', 1, callback_data='send_file')
keyboard_homework.new_button('Установить дату сдачи', 2, callback_data='set_date')
keyboard_homework.new_button('Отправить задание', 3, callback_data='send_homework')

keyboard_homework_add_file = Menu('inline', 1)
keyboard_homework_add_file.new_button('Назад', 1, callback_data='cancel_to_homework')

# Подтверждение выдачи задания — те же кнопки 'confirm'/'cancel', что и в
# каталоге; хендлер требует состояние Homework.confirm_send, поэтому
# колбэк из старого сообщения другого экрана не срабатывает (§2).
keyboard_homework_confirmation = keyboard_catalog_tasks_list_confirm_generic

# keyboard_time_selection импортирован из catalog_tasks_list: там он собран на
# типизированном контракте TimeCb (§1); здесь оставлен псевдоним для старых импортов.
__all__ = ['keyboard_homework', 'keyboard_homework_add_file',
           'keyboard_homework_confirmation', 'keyboard_time_selection']
