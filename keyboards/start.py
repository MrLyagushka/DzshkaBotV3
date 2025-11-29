from utils.menu import Menu

keyboard_start = Menu('reply', 1)
keyboard_start.new_button('Учитель',1)
keyboard_start.new_button('Ученик',1)

keyboard_teacher_start = Menu('reply', 2)
keyboard_teacher_start.new_button('Выдать задание',1)
keyboard_teacher_start.new_button('Список учеников',1)
keyboard_teacher_start.new_button('Профиль',2)

keyboard_student_start = Menu('reply', 2)
keyboard_student_start.new_button('Список заданий', 1)
keyboard_student_start.new_button('Профиль', 2)