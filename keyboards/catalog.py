from utils.menu import Menu

keyboard_catalog = Menu('inline', 2)
keyboard_catalog.new_button('Добавить ученика', 1, callback_data='add_student')
keyboard_catalog.new_button('Список учеников', 2, callback_data='list_students')

keyboard_catalog_student = Menu('inline', 2)
keyboard_catalog_student.new_button('Активные', 1, callback_data='view_active_tasks_student')
keyboard_catalog_student.new_button('На проверке', 1, callback_data='view_check_tasks_student')
keyboard_catalog_student.new_button('Завершенные', 2, callback_data='view_passed_tasks_student')

keyboard_catalog_teacher = Menu('inline', 2)
keyboard_catalog_teacher.new_button('Активные', 1, callback_data='view_active_tasks_teacher')
keyboard_catalog_teacher.new_button('На проверке', 1, callback_data='view_check_tasks_teacher')
keyboard_catalog_teacher.new_button('Завершенные', 2, callback_data='view_passed_tasks_teacher')

keyboard_catalog_student_pass = Menu('inline', 3)
keyboard_catalog_student_pass.new_button('Добавить файл', 1, callback_data='add_file_to_task')
keyboard_catalog_student_pass.new_button('Добавить текст', 2, callback_data='add_text_to_task')
keyboard_catalog_student_pass.new_button('✅ Сдать', 3, callback_data='pass_task')

keyboard_catalog_student_pass_confirm = Menu('inline', 2)
keyboard_catalog_student_pass_confirm.new_button('✅ Подтвердить сдачу', 1, callback_data='confirm_pass_task')
keyboard_catalog_student_pass_confirm.new_button('❌ Отменить', 2, callback_data='cancel_pass_task')

keyboard_catalog_teacher_check = Menu('inline', 2)
# keyboard_catalog_teacher_check.new_button('Добавить комментарий', 1, callback_data='set_comment')
# keyboard_catalog_teacher_check.new_button('Отправить на перепроверку')
keyboard_catalog_teacher_check.new_button('Поставить оценку', 1, callback_data='set_marks')
keyboard_catalog_teacher_check.new_button('Отметить как решенное', 2, callback_data='set_passed')

keyboard_catalog_teacher_check_passed_task = Menu('inline', 2)
# keyboard_catalog_teacher_check_passed_task.new_button('Добавить комментарий', 1, callback_data='set_comment')
# keyboard_catalog_teacher_check_passed_task.new_button('Отправить на перепроверку')
keyboard_catalog_teacher_check_passed_task.new_button('Поставить оценку', 1, callback_data='set_marks_pased_task')

keyboard_choice_marks = Menu('inline', 3)
keyboard_choice_marks.new_button('5', 1, callback_data='mark5')
keyboard_choice_marks.new_button('4', 2, callback_data='mark4')
keyboard_choice_marks.new_button('3', 3, callback_data='mark3')
keyboard_choice_marks.new_button('2', 3, callback_data='mark2')

keyboard_catalog_teacher_pass_confirm = Menu('inline', 2)
keyboard_catalog_teacher_pass_confirm.new_button('✅ Подтвердить', 1, callback_data='confirm')
keyboard_catalog_teacher_pass_confirm.new_button('❌ Отменить', 2, callback_data='cancel')