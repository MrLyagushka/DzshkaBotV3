from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
import logging
from aiogram.fsm.context import FSMContext

from utils.template import DinamicKeyboard
from utils.callbacks import PageCb

router_service_handlers = Router()


@router_service_handlers.callback_query(PageCb.filter())
async def on_the_what(callback: CallbackQuery, callback_data: PageCb):
    await callback.answer()
    first_index = callback_data.first_index
    if callback_data.direction == 'prev':
        first_index = first_index - 1 if first_index > 0 else first_index
    elif callback_data.direction == 'next':
        first_index = first_index + 1 if callback_data.total > first_index + callback_data.row*callback_data.column else first_index
    if first_index != callback_data.first_index:
        button_info = f'{callback_data.kind}_{callback_data.owner_id}_{callback_data.mode}'
        # Пагинация работает только для inline-сообщений; при inline_message_id=None
        # (кнопки в обычном сообщении) редактировать нечего — молча выходим.
        if callback.inline_message_id is None:
            return
        await callback.message.edit_reply_markup(inline_message_id=callback.inline_message_id,
                                             reply_markup=DinamicKeyboard(row=callback_data.row,
                                                                          column=callback_data.column,
                                                                          is_always_bigger_column_multiply_row=callback_data.is_always_bigger,
                                                                          first_index=first_index,
                                                                          button_info=button_info).generate_keyboard())
