from utils.menu import Menu

keyboard_catalog_main_menu = Menu('inline', 2)
keyboard_catalog_main_menu.new_button('Добавить ученика', 1, callback_data='add_student')
keyboard_catalog_main_menu.new_button('Список учеников', 2, callback_data='list_students')