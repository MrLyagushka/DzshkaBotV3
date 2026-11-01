from utils.menu import Menu

keyboard_catalog_main_menu = Menu('inline', 2)
keyboard_catalog_main_menu.new_button('Добавить ученика', 1, callback_data='add_student')
keyboard_catalog_main_menu.new_button('Удалить ученика', 1, callback_data='delete_student')
keyboard_catalog_main_menu.new_button('Список учеников', 2, callback_data='list_students')

keyboard_catalog_main_menu_confirm = Menu('inline', 1)
keyboard_catalog_main_menu_confirm.new_button('✅ Подтвердить удаление', 1, callback_data='confirm_delete_student')
keyboard_catalog_main_menu_confirm.new_button('❌ Отменить', 1, callback_data='cancel_delete_student')
# §4: confirm-экран one-shot — после терминального действия кнопки снимаются
keyboard_catalog_main_menu_confirm.clear_markup = True