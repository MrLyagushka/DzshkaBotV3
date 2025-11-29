from utils.menu import Menu

keyboard_profile_teacher = Menu('inline',2)
keyboard_profile_teacher.new_button('Сбросить имя', 1, callback_data='reset_name')
keyboard_profile_teacher.new_button('Сбросить регистрацию', 2, callback_data='reset_registration')


keyboard_profile_student = Menu('inline', 2)
keyboard_profile_student.new_button('Сбросить имя', 1, callback_data='reset_name')
keyboard_profile_student.new_button('Сбросить регистрацию', 2, callback_data='reset_registration')
