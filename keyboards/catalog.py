from utils.menu import Menu

keyboard_catalog = Menu('inline', 2)
keyboard_catalog.new_button('Добавить ученика', 1, callback_data='add_student')
keyboard_catalog.new_button('Список учеников', 2, callback_data='list_students')

keyboard_catalog_student = Menu('inline', 2)
keyboard_catalog_student.new_button('Активные', 1, callback_data='view_active_tasks')
keyboard_catalog_student.new_button('Завершенные', 2, callback_data='view_passed_tasks')

keyboard_catalog_student_pass = Menu('inline', 3)
keyboard_catalog_student_pass.new_button('Добавить файл', 1, callback_data='add_file_to_task')
keyboard_catalog_student_pass.new_button('Добавить текст', 2, callback_data='add_text_to_task')
keyboard_catalog_student_pass.new_button('✅ Сдать', 3, callback_data='pass_task')

keyboard_catalog_student_pass_confirm = Menu('inline', 2)
keyboard_catalog_student_pass_confirm.new_button('✅ Подтвердить сдачу', 1, callback_data='confirm_pass_task')
keyboard_catalog_student_pass_confirm.new_button('❌ Отменить', 2, callback_data='cancel_pass_task')