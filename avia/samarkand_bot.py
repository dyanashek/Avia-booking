import os
import datetime

import django

import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from money_transfer.models import Manager, Transfer, Delivery, Status
from money_transfer.utils import update_transfer_pass_status

import config
import keyboards
import utils


bot = Bot(token=config.TELEGRAM_SAMARKAND_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_message(message: types.Message):
    user_id = str(message.from_user.id)
    is_exists = sync_to_async(Manager.objects.filter(telegram_id=user_id).exists)()
    if is_exists:
        await bot.send_message(chat_id=user_id,
                         text='Привет.\nЗдесь можно контролировать выдачу денежных средств.\nОтправьте код получателя для вывода информации и внесения изменений.',
                         )
    else:
        await bot.send_message(chat_id=user_id,
                         text='Доступ закрыт.\nОбратитесь к администратору.',
                         )


@dp.callback_query()
async def callback_query(call: types.CallbackQuery):
    """Handles queries from inline keyboards."""

    user_id = str(call.from_user.id)

    user = await sync_to_async(Manager.objects.filter(telegram_id=user_id).first)()
    if user:
        message_id = call.message.message_id
        chat_id = call.message.chat.id
        call_data = call.data.split('_')
        query = call_data[0]

        if query == 'cancel':
            await bot.edit_message_reply_markup(message_id=message_id,
                                                chat_id=chat_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
        elif query == 'pass':
            transfer_id = int(call_data[1])
            await bot.edit_message_reply_markup(message_id=message_id,
                                                chat_id=chat_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )

            transfer = await sync_to_async(Transfer.objects.filter(id=transfer_id).first)()
            if transfer:
                curr_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3))
                transfer.pass_date = curr_date
                curr_date = curr_date.strftime('%d.%m.%Y %H:%M')
                await sync_to_async(transfer.save)()
                try:
                    await update_transfer_pass_status(transfer_id, curr_date)
                except:
                    pass

                await bot.send_message(chat_id=user_id,
                         text='Перевод помечен как выданный.',
                         )
            else:
                await bot.send_message(chat_id=user_id,
                         text='Данные устарели.',
                         )


@dp.message(F.text)
async def handle_text(message):
    """Handles message with type text."""

    user_id = str(message.from_user.id)

    user = await sync_to_async(Manager.objects.filter(telegram_id=user_id).first)()
    input_info = await utils.escape_markdown(message.text)

    if user:
        transfer_id = await utils.validate_id(input_info)

        if transfer_id:
            transfer = await sync_to_async(Transfer.objects.filter(id=transfer_id).first)()

            if transfer:
                delivery: Delivery = await sync_to_async(lambda: transfer.delivery)()
                sender = await sync_to_async(lambda: delivery.sender)()
                sender_address = await sync_to_async(lambda: delivery.sender_address)()
                sender_address = sender_address.address
                receiver = await sync_to_async(lambda: transfer.receiver)()
                receiver_address = await sync_to_async(lambda: transfer.address)()
                if receiver_address:
                    receiver_address = receiver_address.address
                else:
                    receiver_address = 'не указан'
            
                if transfer.pick_up:
                    pick_up = 'да'
                else:
                    pick_up = 'нет'
                
                pass_date = transfer.pass_date
                if pass_date:
                    pass_date = pass_date.strftime('%d.%m.%Y %H:%M')
                else:
                    pass_date = 'не выдано'

                reply_text = f'''
                            *Отправитель:*\
                            \nИмя: *{sender.name}*\
                            \nНомер: *{sender.phone}*\
                            \nАдрес: *{sender_address}*\
                            \nСтатус в системе: *{delivery.status_message}*\
                            \n\
                            \n*Получатель:*\
                            \nКод: *{transfer.pk}*\
                            \nИмя: *{receiver.name}*\
                            \nНомер: *{receiver.phone}*\
                            \nДоставка: *{pick_up}*\
                            \nАдрес: *{receiver_address}*\
                            \nВыдано: *{pass_date}*\
                            '''
                
                status: Status = await sync_to_async(lambda: delivery.status)()
                if status.slug == 'finished' and pass_date == 'не выдано':
                    keyboard = await keyboards.pass_money_keyboard(transfer.pk)
                else:
                    keyboard = InlineKeyboardBuilder().as_markup()

                await bot.send_message(chat_id=user_id,
                         text=reply_text,
                         reply_markup=keyboard,
                         parse_mode='Markdown',
                         )

            else:
                await bot.send_message(chat_id=user_id,
                         text='Перевода с таким кодом не найдено.',
                         )
        else:
            await bot.send_message(chat_id=user_id,
                         text='Не похоже на код получателя, должно быть целое число.',
                         )

                
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())