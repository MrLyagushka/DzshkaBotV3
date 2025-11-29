from utils.menu import Menu

keyboard_homework = Menu('inline', 3)
keyboard_homework.new_button('Прикрепить файл', 1, callback_data='send_file')
keyboard_homework.new_button('Установить дату сдачи', 2, callback_data='set_date')
keyboard_homework.new_button('Отправить задание', 3, callback_data='send_homework')





