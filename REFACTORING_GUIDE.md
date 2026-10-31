# Инструкции для самого себя: рефакторинг и исправление ошибок доступа между сообщениями

Рабочая база: aiogram 3.22 (`Bot`, `Dispatcher`, `Router`, `FSMContext`), SQLite (два файла БД:
users — `PATH_TO_DB_USERS`, tasks — `PATH_TO_DB_TASK`). Ключевые файлы:
`main.py`, `handlers/*.py`, `keyboards/*.py`, `utils/{template,users,catalog,menu,filter}.py`.

Главный класс проблем — **«ошибки доступа между сообщениями»**: состояние FSM и данные
(`selected_task_id`, `id_student`, `callback_data`, `added_text`, ...) хранятся в одном контексте
на диалог (user+chat) и при этом:
- читаются без проверки принадлежности текущему пользователю;
- не сбрасываются между экранами/сессиями;
- используются из «старых» сообщений (кнопки под сообщением остаются живыми навсегда);
- фильтруются хрупкими строковыми срезами `F.data[:16] == ...`, из-за чего обработчики
  перекрывают друг друга и ловят чужие колбэки.

---

## 0. Правила процесса (обязательно для каждого шага)

1. Один шаг = один коммит. Перед правкой — `git diff` пустой; после — `python -m py_compile` всех
   изменённых файлов и ручной прогон сценариев из раздела «Тест-план» (§8).
2. Не менять формат callback_data «на глаз»: сначала §1 (единые контракты), потом §2–§5.
3. Каждое исправление доступа сопровождается тестом: «открыть два чата у одного пользователя»,
   «нажать кнопку под старым сообщением», «выбрать ученика A, затем B, вернуться к экрану A».
4. Никаких новых `except Exception: print(...)`. Ошибки — только через `logging` с именем функции.

---

## 1. Единые контракты callback_data (база для всего остального)

Проблемы сейчас:
- `utils/template.py` генерирует `callback_data_st_<Имя>_<id>` и `callback_datatsa_<дд.мм>_<id>`
  (префикс слипается: `callback_datatsa`, а разделитель `_` внутри имени/даты ломает `split('_')[N]`).
- Имена учеников содержат пробелы и `_` → `int(callback.data.split('_')[4])` может упасть или
  взять не тот индекс.
- Обработчики фильтруют по `F.data[:16]`, что совпадает и с кнопками пагинации, и с чужими экранами.
- В `catalog_main_menu.py` для удаления используется `F.data[:17] == 'callback_data_ds_'`, а в
  `catalog_tasks_list.py` — `F.data[:16] == 'callback_data_st'`: `st` — подстрока `ds` на той же
  позиции, поэтому колбэк чужого экрана может быть перехвачен не тем роутером (плюс оба хендлера
  зарегистрированы без проверки FSM-состояния выбора).

Сделать:
1. В `utils/template.py` определить типизированные CallbackData-классы вместо строк:
   ```python
   class StudentCb(CallbackData, prefix="st"):      # st:id
       id: int
   class TaskCb(CallbackData, prefix="t"):          # t:mode:id  mode in a|d|p
       mode: Literal["a", "d", "p"]
       id: int
   class DelStudentCb(CallbackData, prefix="ds"):   # ds:id
       id: int
   ```
   `DinamicKeyboard.generate_keyboard()` должен упаковывать их через `.pack()`. Текст кнопки —
   `f"{name} ({id})"` (требование пользователя №2: id виден всегда, а не только в ответном сообщении).
2. Во всех handlers заменить `F.data[:16] == '...'` + `split('_')` на `StudentCb.filter()` /
   `TaskCb.filter()` с автопарсингом (`async def h(cb: CallbackQuery, cb_data: TaskCb, ...)`).
   Убрать магические индексы `[3]`, `[4]` полностью.
3. Проверить лимит Telegram (64 байта) — в новых префиксах передаём только числа, лимит нестрашен.
4. Удалить мёртвые ветки `tt` (закомментированный код в `template.py`).

Критерий готовности: ни одного `callback.data.split('_')` вне сервисных обработчиков; ни одного
`F.data[:N] ==`.

✅ **СТАТУС (выполнено):** создано `utils/callbacks.py` — `StudentCb(mode='view'|'del', student_id:int)`,
`TaskCb(mode='a'|'d'|'p', task_id:int)`, `PageCb(direction, first_index, row, column, kind, mode)`
(разделитель `:`, имена кнопок в payload не попадают); `filter(mode=...)` реализован через подкласс
`CallbackQueryFilter` (в aiogram 3.22 `CallbackData.filter` принимает только magic-`rule`).
`utils/template.py`: генерация кнопок через `.pack()`, текст кнопки «Имя (id)»
(`student_button_text`), мёртвые ветки `tt`/`MyCallbackData` удалены, пагинация — `PageCb`.
Переведены хендлеры: `homework1`, `catalog16/delete/confirm`, `catalog17`, `catalog6/15/19/21/29/31`,
`service_handlers.on_the_what`. Оставшиеся `split('_')` — только разбор статичных кнопок времени
`time_HH` (без пользовательских данных, безопасно). Round-trip тесты фильтров пройдены,
`main.py` импортируется со всеми роутерами.

---

## 2. FSM: состояния как экраны + обязательный сброс

Проблемы сейчас:
- В `catalog28` ставится `CatalogTasksList.fifth`, но это состояние НИ в одном фильтре не используется
  (`fifth` объявлен только в `Homework`). Итог: после открытия «Задания на проверке» у ученика
  колбэки `callback_datatsp_*` не матчатся ни на один хендлер (`catalog29` требует
  `view_active_tasks_student`) и «молча» игнорируются.
- Те же `tsa/tsd/tsa(p)`-колбэки учителя (`catalog19/21/31`) требуют `view_active_tasks_teacher`,
  хотя открыты были из экранов passed/check — совпадение состояния обеспечивается случайно.
- После завершения операций состояние часто НЕ сбрасывается: `catalog17` (выбор ученика),
  `catalog19/21/31` (просмотр задания учителем), `catalog22–27` (оценки/подтверждения),
  `catalog12` (сдача задания), `homework1..` — пользователь «застревает» в состоянии экрана, и
  следующие его сообщения перехватываются старыми message-хендлерами (например, любой текст
  после `add_text_to_task` молча пишется в ответ к заданию).
- `state.clear()` есть только в flow удаления ученика (`catalog_main_menu.py`) и в `profile`.

Сделать:
1. Переименовать `CatalogTasksList.fifth` → `view_check_tasks_student`; в `catalog28` ставить его,
   а фильтры `callback_datatsp` для ученика (`catalog29`) и учителя (`catalog31`) перевести на
   собственные состояния экрана (сейчас у обоих ошибочно стоит `view_active_tasks_*`).
   Должно действовать правило: **состояние = экран, с которого пришёл колбэк; фильтр хендлера обязан
   совпадать с состоянием, которое ставит родительский экран** (tsa→active, tsd→passed, tsp→check;
   отдельно student/teacher).
2. Для каждого терминального действия (сдал задание, выставил оценку, подтвердил/отменил удаление,
   отправил на дорешку, изменил дедлайн) — явный `await state.clear()` в `finally` обработчика либо
   переход в «корневое» состояние роли. Правило: **хендлер, отвечающий финальное сообщение экрана,
   обязан clear или set_state осознанно**.
3. Точка входа: при нажатии главных кнопок меню («Список заданий», «Выдать задание», «Профиль»,
   `/start`) всегда делать `await state.clear()` перед входом в новый флоу — это гасит перенос
   stale-данных между несвязанными экранами.
4. Кнопки «❌ Отменить / Назад» во всех confirm-клавиатурах должны выполнять `state.clear()`,
   а не только в delete_student.

Критерий готовности: прогон §8 сценариев S3–S6 без «залипания» в состояниях.

✅ **СТАТУС (выполнено):**
- `CatalogTasksList.fifth` удалён; вместо него экран `view_check_tasks_student`, который ставит
  `catalog28`; фильтры просмотра задания переведены по правилу «состояние = экран родителя»:
  tsa→`view_active_tasks_*`, tsd→`view_passed_tasks_*`, tsp→`view_check_tasks_*` (student/teacher
  отдельно) — баг «молча не работающих» кнопок «Задания на проверке» закрыт.
- Новые экраны-состояния: `confirm_pass` (сдача учеником), `confirm_set_passed` (отметка «решено»
  учителем, каталог), `set_mark` (ожидание нажатия 2/3/4/5), `change_deadline` (дедлайн),
  `add_file_done` (служебный, сбор альбома фото), `Homework.confirm_send` (подтверждение выдачи).
- Общая клавиатура подтверждения `keyboard_catalog_tasks_list_confirm_generic` ('confirm'/'cancel')
  используется во всех трёх экранах; колбэки различаются ТОЛЬКО state-фильтром, конфликт
  «живой кнопки из прошлого сообщения» устранён. Старые 'confirm_send'/'confirm_cancel' в homework
  заменены на те же 'confirm'/'cancel' + `Homework.confirm_send`.
- Хелпер `reset_flow(state)` (`handlers/catalog_tasks_list.py`): `state.clear()` + обнуление
  черновиков (added_text/file_*/selected_task_id/id_student); вызывается на каждом терминальном
  шаге и в ветках except (сдача задания catalog12, оценки catalog24, подтверждение/отмена
  catalog25–27, дедлайн catalog35/37, отмены confirm_pass/confirm_set_passed/set_mark/
  change_deadline; homework9/10/11 — `state.clear()` напрямую).
- Точки входа в новые флоу делают сброс перед входом; message-хендлеры ввода текста/файла
  (`add_text_to_task`, загрузка файлов) требуют состояние экрана и закрывают его после приёма —
  обычный текст больше не перехватывается старым экраном.
- Проверки сессий в homework11 (`student_id is None` → «Сессия устарела» + clear) и catalog12
  (`selected_task_id is None` → аналогично + reset_flow).
- Фильтры времени/оценок типизированы: `TimeCb.filter()` (homework7, catalog35),
  `MarkCb.filter()` (catalog24) — старых срезов `F.data[:4]=='time'` / `data[4]` не осталось.

Проверено: `python -m py_compile` всех файлов; импорт `main.py` и сборка Dispatcher (8 роутеров);
round-trip и negative-тесты фильтров MarkCb/TimeCb/StudentCb/TaskCb (форматы `mark5`, `time_18`,
`callback_data_st_Иван_5` отклоняются).

---

## 3. Данные FSM ≠ права доступа: проверки владельца (главная часть «доступа между сообщениями»)

Уязвимости сейчас (все — чтение `state.get_data()` без проверки, что запись относится к текущему
`from_user.id`):
- `catalog18/20/30, catalog19/21/31, catalog24/26/27`: берут `id_student` из FSM. Если учитель А
  когда-то выбирал ученика X, а теперь работает с Y, любое «старое» inline-сообщение (кнопки живы!)
  вернёт данные X. Итог: просмотр/оценка чужого ученика.
- `catalog12` (сдача задания): `save_answer_task(id_task=...)` без проверки `task.id_student ==
  from_user.id` → ученик может сдать чужое задание кнопкой со старого сообщения.
- `catalog24` (оценка): `set_marks(state['selected_task_id'], ...)` без проверки, что задача
  принадлежит ученику из текущего выбора и что её учитель == from_user.id.
- `catalog35/37` (дедлайн, отправка на дорешку): аналогично — нет `get_id_teacher(task) == user`.
- `catalog_delete_student_confirm`: принимает ЛЮБОЙ `callback_data_ds_*` даже без состояния
  `delete_student_id` и без проверки, что student id ∈ списка учителя (проверка есть только на
  финальном `confirm`). Между двумя нажатиями можно вручную отправить чужой callback.
- `utils/catalog.add_student`: принимает произвольный id ученика, существование проверяется
  косвенно (`KeyError`), привязка происходит даже если у ученика уже есть другой учитель
  (перехват чужого ученика).

Сделать:
1. Центральный guard-хелпер в `utils/access.py`:
   ```python
   def ensure_task_for_student(task_row, student_id): ...
   def ensure_task_for_teacher(task_row, teacher_id): ...
   def ensure_student_of_teacher(student_id, teacher_id): ...  # уже есть в Teacher.is_student_of_teacher
   ```
   Каждый handler, использующий `selected_task_id`/`id_student`, обязан:
   a) получить строку задачи из БД по id; б) сверить `task.id_student`/`task.id_teacher` с
   `callback.from_user.id`; в) при несовпадении — ответить «Сообщение устарело, начните заново» и
   сделать `state.clear()`.
2. Хранить в FSM не только id, но и владельца: `update_data(ctx_owner=user_id, ...)`, и при каждом
   `get_data()` сверять `data['ctx_owner'] == from_user.id`, иначе clear. Это защищает от
   «общих» данных в групповых чатах (ключ FSM = chat+user, но один пользователь = много чатов).
3. `add_student`: перед UPDATE читать текущий `id_teacher`; если уже занят другим — сообщать
   «Ученик уже привязан к другому преподавателю». Существование — яжным `fetchone() is None`,
   а не try/except KeyError.
4. `catalog_delete_student_confirm`: требовать активное состояние `CatalogMainMenu.delete_student_id`
   (добавить State-фильтр к хендлеру) и сразу проверять `is_student_of_teacher`.
5. Все DB-функции (`set_pass`, `set_marks`, `update_deadline`, `return_goback`, `save_answer_task`)
   принять опциональный параметр ожидаемого владельца и добавлять его в `WHERE`
   (`... WHERE id = ? AND id_student = ?`), возвращать `rowcount` — тогда проверка становится
   атомарной и двойная защита (handler + SQL).

Критерий готовности: сценарии S7–S10 (§8) дают отказ, а не действие.

---

## 4. Устаревшие сообщения: edit vs answer, идемпотентность

Проблемы: почти везде `callback.message.answer(...)` — старые клавиатуры накапливаются и остаются
кликабельными; именно они и порождают «доступ между сообщениями».

Сделать:
1. Экраны заменять на месте: `callback.message.edit_text/edit_reply_markup` (+ `edit_media` для
   документов) вместо нового `answer` там, где это замена контента (списки, выбор, подтверждения).
   Для `answer_document` — оставить отправку, но после неё удалять inline-клавиатуру старого
   сообщения: `await callback.message.edit_reply_markup(reply_markup=None)`.
2. Правило one-shot для confirm-кнопок (`confirm_delete_student`, `confirm_pass_task`, `confirm`,
   `set_passed`...): первым делом `edit_reply_markup(None)` — нельзя подтвердить дважды.
3. `catalog24` вызывает `await callback.answer()` ДВАЖДЫ — второй выбрасывает «query is already
   answered», который проглатывается внешним try → лог-шум и сбой second-half. Оставить один.
4. `service_handlers.on_the_what` использует `inline_message_id` для `edit_reply_markup` — при
   пустом значении падает; добавить fallback на `callback.message`. Также пагинация переживает
   удаление ученика: при выходе `first_index` за границы списка — перегенерировать с 0.

---

## 5. Чистка логики и обработка ошибок (рефакторинг «по мелочи», но важно)

1. `utils/users.py`: методы глотают исключения через `print` и оставляют атрибуты
   (`students_info`, `name_student`, `homework_active`) unset → ниже `AttributeError`/`KeyError`.
   Инициализировать атрибуты значениями по умолчанию в `__init__`, поднять `DbError` наружу,
   ловить в хендлерах одним шаблоном. Заодно заменить классы-«структуры» на dataclass-возвраты
   (`Teacher.students: list[StudentRef]`).
2. `handlers/catalog_main_menu.catalog3` (добавление по id): проверка существования — через
   `if not student.name_student:` вместо `KeyError` в try; убрать тройной дубль `try`.
3. `handlers/catalog_tasks_list.py`:
   - `special_function` определена ДВАЖДЫ (строки ~289 и ~320) — вторая затирает первую; удалить
     дубликат, оставив одну параметризованную версию `(source: Message|CallbackQuery, state, role)`.
   - `special_function_callback_not_callback` — почти копия `special_function`, только для
     CallbackQuery; объединить их в одну функцию с параметром `source: Message | CallbackQuery`.
   - `catalog25` пишет `callback_data='set_marks'` вместо `'set_passed'` — из-за этого после
     «Назад» (`catalog27`) показывается не тот экран. Починить значение.
   - `catalog26` читает `data['marks']` ДО выставления оценки — уточнить смысл уведомления ученику
     («вам выставили оценку None»); отправлять уведомление только при наличии marks, иначе —
     «задание завершено».
   - `catalog28` ставит неиспользуемое `CatalogTasksList.fifth` (см. §2.1) — из-за этого кнопки
     «заданий на проверке» у ученика не работают вообще.
   - `catalog37` при успехе ставит `CatalogTasksList.time` — остаточное состояние; вместо этого
     `state.clear()`.
   - `catalog17`: `update_data(id_student=...)` — привести к int и записать `ctx_owner` (§3.2).
4. `handlers/homework.py`: вызовы `message.answer(...)` без `await` (start1/homework0 в except) —
   добавить await; корутины не выполняются, ошибки молча теряются. То же в `utils/*` нигде быть не
   должно (проверить grep `^\s+[a-z_]+\.answer\(` без await).
5. `handlers/start.start1`: трижды вызывается `are_you_new_user` (три запроса к БД, race) — сохранить
   результат в переменную.
6. `utils/filter.is_student/is_teacher` загружают ВСЕХ пользователей ради проверки одной роли —
   заменить на `SELECT 1 FROM teacher WHERE id = ?` (`utils/access.is_teacher(id)`). Используется в
   profile1, start1 — горячий путь.
7. `main.py`: `Bot(token)` создаётся на импорте модуля — перенося в `main()`; `dp.start_polling(bot)`
   c явной передачей бота; `scheduler.add_job` не трогать.
8. Логирование: во всех хендлерах унифицировать `except Exception as e: logging.exception(f"...")`
   и ответ «❌Ошибка, обратитесь в поддержку» — сейчас часть путей отвечает без await или молчит.
9. `utils/template.DinamicKeyboard`: конструктор принимает `button_info` строкой с embedded id
   учителя/ученика — разделить на `kind` + `owner_id` параметры; источник кнопок — список пар
   `(text, payload)`, генерируемый вызывающим кодом (UBML-подобный слой), чтобы template не лазил
   в БД сам. Это снимает скрытую повторную загрузку данных и рассинхрон с реальным списком.

---

## 6. Порядок выполнения (зависимости)

1. §1 контракты callback_data (+ обновление `template.py`, все фильтры) — всё остальное опирается.
2. §3 access-guard + владелец в FSM (сначала read-проверки, затем SQL-параметры).
3. §2 FSM-состояния/сбросы (после того как колбэки точно типизированы).
4. §4 edit-vs-answer и one-shot confirm.
5. §5 чистка (дубликаты функций, await, логирование) — параллельно с 2–4, но отдельными коммитами.
6. §7 регрессионные тесты, затем полировка.

---

## 7. Мини-тесты (pytest; dispatch aiogram можно эмулировать fake-объектами)

Минимальный набор unit-тестов без сети (fake `CallbackQuery` с `from_user`, state-memory backend):
- `test_task_cb_pack_parse`: roundtrip `TaskCb(mode='a', id=7).pack()` → filter-парсинг.
- `test_add_student_rejects_taken`: ученик уже с id_teacher=T1, добавление T2 → False/сообщение.
- `test_remove_student_wrong_teacher`: remove(id_student, other_teacher) → rowcount==0.
- `test_set_marks_requires_owner`: set_marks(task, mark, expected_teacher=wrong) → ничего не обновлено.
- `test_catalog17_sets_int_and_owner`: после выбора ученика ctx содержит int + ctx_owner.
- `test_stale_confirm_denied`: ctx.selected_task_id принадлежит др. пользователю → handler отвечает
  «устарело» и делает clear.
Интеграционный smoke: два пользователя (учитель/ученик) проходят полный цикл выдача→ответ→сдача→
оценка→завершение; после каждого терминального шага assert `await state.get_state() is None`.

---

## 8. Тест-план ручного прогона (сценарии «доступа между сообщениями»)

- S1: учитель выбирает ученика A, открывает «Активные задания», выходит в меню, выбирает B — экран
  показывает задания B (не A).
- S2: показать id ученика на кнопках и в сообщении выбора (требование пользователя).
- S3: ученик сдаёт задание → сразу печатает произвольный текст → он НЕ попадает в ответ задания.
- S4: после «Оценка установлена» старые кнопки оценок неактивны (edit/clear markup).
- S5: двойное нажатие «✅ Подтвердить удаление» — второй клик игнорируется.
- S6: «❌ Отменить» в любом confirm возвращает в меню с `state=None`.
- S7: учитель А жмёт кнопку просмотра из сообщения, созданного, когда был выбран ученик X (не его) —
  получает «сообщение устарело».
- S8: ученик пытается сдать чужой task_id (вручную сконструированный callback) — отказ.
- S9: пагинация '>' до конца списка, затем удаление ученика, затем '<' — без падения.
- S10: два чата одного учителя (ЛС и группа-чат с ботом, если доступно) — данные не пересекаются
  (ctx_owner).

---

## 9. Definition of Done

- Нет `F.data[:N] ==`, нет `split('_')[k]` для бизнес-id, нет `print` в utils, нет `answer` без await.
- Каждый handler с `get_data()` содержит проверку владельца ИЛИ SQL-условие с id владельца.
- Все терминальные шаги делают `state.clear()`; все confirm-кнопки one-shot.
- Тесты §7 зелёные; сценарии S1–S10 проходят вручную; `git log` — по коммиту на шаг.
