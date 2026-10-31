from utils.menu import Menu
from utils.callbacks import MarkCb, TimeCb

keyboard_catalog_tasks_list_student = Menu('inline', 2)
keyboard_catalog_tasks_list_student.new_button('Активные', 1, callback_data='view_active_tasks_student')
keyboard_catalog_tasks_list_student.new_button('На проверке', 1, callback_data='view_check_tasks_student')
keyboard_catalog_tasks_list_student.new_button('Завершенные', 2, callback_data='view_passed_tasks_student')

keyboard_catalog_tasks_list_teacher = Menu('inline', 2)
keyboard_catalog_tasks_list_teacher.new_button('Активные', 1, callback_data='view_active_tasks_teacher')
keyboard_catalog_tasks_list_teacher.new_button('На проверке', 1, callback_data='view_check_tasks_teacher')
keyboard_catalog_tasks_list_teacher.new_button('Завершенные', 2, callback_data='view_passed_tasks_teacher')

keyboard_catalog_tasks_list_student_pass = Menu('inline', 3)
keyboard_catalog_tasks_list_student_pass.new_button('Добавить файл к ответу', 1, callback_data='add_file_to_task')
keyboard_catalog_tasks_list_student_pass.new_button('Добавить текст к ответу', 2, callback_data='add_text_to_task')
keyboard_catalog_tasks_list_student_pass.new_button('✅ Сдать', 3, callback_data='pass_task')

# Отмена ожидания ввода (текст/файл) — обязательный сброс FSM (§2 плана)
keyboard_catalog_tasks_list_cancel_input = Menu('inline', 1)
keyboard_catalog_tasks_list_cancel_input.new_button('❌ Отменить', 1, callback_data='cancel_add_text')

# Универсальное подтверждение «да/нет» для терминальных шагов:
# сдача задания учеником (confirm_pass), отметка «решено» учителем
# (confirm_set_passed), выдача задания (Homework.confirm_send).
# Хендлеры confirm/cancel различают экран по FSM-состоянию (§2), поэтому одна
# клавиатура годится во всех местах и не оставляет живых кнопок от прошлого экрана.
keyboard_catalog_tasks_list_confirm_generic = Menu('inline', 2)
keyboard_catalog_tasks_list_confirm_generic.new_button('✅ Подтвердить', 1, callback_data='confirm')
keyboard_catalog_tasks_list_confirm_generic.new_button('❌ Отменить', 2, callback_data='cancel')

keyboard_catalog_tasks_list_student_pass_confirm = keyboard_catalog_tasks_list_confirm_generic
keyboard_catalog_tasks_list_teacher_pass_confirm = keyboard_catalog_tasks_list_confirm_generic

keyboard_catalog_tasks_list_teacher_check = Menu('inline', 2)
keyboard_catalog_tasks_list_teacher_check.new_button('Поставить оценку', 1, callback_data='set_marks')
keyboard_catalog_tasks_list_teacher_check.new_button('Отметить как решенное', 1, callback_data='set_passed')
keyboard_catalog_tasks_list_teacher_check.new_button('Изменить дедлайн', 2, callback_data='change_deadline')
keyboard_catalog_tasks_list_teacher_check.new_button('На дорешку', 2, callback_data='return')

keyboard_catalog_tasks_list_teacher_check_passed_task = Menu('inline', 2)
keyboard_catalog_tasks_list_teacher_check_passed_task.new_button('Поставить оценку', 1, callback_data='set_marks_pased_task')

keyboard_choice_marks = Menu('inline', 3)
# Типизированный контракт вместо склейки 'mark5' + среза data[4] (§1/§2)
keyboard_choice_marks.new_button('5', 1, callback_data=MarkCb(value=5).pack())
keyboard_choice_marks.new_button('4', 2, callback_data=MarkCb(value=4).pack())
keyboard_choice_marks.new_button('3', 3, callback_data=MarkCb(value=3).pack())
keyboard_choice_marks.new_button('2', 3, callback_data=MarkCb(value=2).pack())

# Часы дедлайна: тот же типизированный контракт TimeCb, что и в homework,
# чтобы один и тот же фильтр работал в обоих роутерах (§1/§2).
keyboard_time_selection = Menu('inline', 5)
for _hour in range(24):
    keyboard_time_selection.new_button(f'{_hour:02}', _hour // 5 + 1,
                                       callback_data=TimeCb(hour=_hour).pack())
keyboard_time_selection.new_button('Назад', 5, callback_data='cancel_time_selection')
