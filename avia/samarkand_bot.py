import os
import datetime

import django

import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from django.db.models import Q

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from money_transfer.models import Manager, Transfer, Delivery, Status, Balance
from money_transfer.utils import update_transfer_pass_status
from errors.models import AppError

import config
import keyboards
import utils


bot = Bot(token=config.TELEGRAM_SAMARKAND_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_message(message: types.Message):
    user_id = str(message.from_user.id)
    user = await sync_to_async(Manager.objects.filter(telegram_id=user_id).first)()
    if user:
        try:
            await bot.send_message(chat_id=user_id,
                            text='Привет.\nЗдесь можно контролировать выдачу денежных средств.\nОтправьте код получателя для вывода информации и внесения изменений.',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='3',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

    else:
        try:
            await bot.send_message(chat_id=user_id,
                            text='Доступ закрыт.\nОбратитесь к администратору.',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='3',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass


@dp.message(Command("delivery"))
async def delivery_message(message: types.Message):
    user_id = str(message.from_user.id)
    user = await sync_to_async(Manager.objects.filter(telegram_id=user_id).first)()
    if user:
        transfers =  await sync_to_async(lambda: list(Transfer.objects.filter(
            Q(pass_date__isnull=True) & 
            Q(pick_up=True) &
            Q(delivery__valid=True) &
            Q(delivery__status__slug='finished')).all()))()
        transfers_ids = ', '.join([str(transfer.id) for transfer in transfers])

        credit_transfers =  await sync_to_async(lambda: list(Transfer.objects.filter(
            Q(pass_date__isnull=True) & 
            Q(pick_up=True) &
            Q(delivery__valid=True) &
            Q(delivery__status__slug='api')).all()))()
        credit_transfers_ids = ', '.join([str(transfer.id) for transfer in credit_transfers])

        try:
            await bot.send_message(chat_id=user_id,
                            text=f'*Требуется доставка:*\n*Можно выдать:* {transfers_ids}\n*Можно выдать в кредит:* {credit_transfers_ids}',
                            parse_mode='Markdown',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='3',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

    else:
        try:
            await bot.send_message(chat_id=user_id,
                            text='Доступ закрыт.\nОбратитесь к администратору.',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='3',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass


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
            try:
                await bot.edit_message_reply_markup(message_id=message_id,
                                                    chat_id=chat_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='3',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

        elif query == 'pass' or query == 'credit':
            transfer_id = int(call_data[1])

            try:
                await bot.edit_message_reply_markup(message_id=message_id,
                                                    chat_id=chat_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='3',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            transfer = await sync_to_async(Transfer.objects.filter(id=transfer_id).first)()
            if transfer:
                curr_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3))
                transfer.pass_date = curr_date
                curr_date = curr_date.strftime("%d.%m.%Y %H:%M")

                if query == 'credit':
                    transfer.credit = True
                    credit = 'Да'
                else:
                    transfer.credit = False
                    credit = 'Нет'

                await sync_to_async(transfer.save)()

                try:
                    balance = await sync_to_async(Balance.objects.get)(id=1)
                    balance.balance -= transfer.usd_amount
                    await sync_to_async(balance.save)()
                except:
                    pass

                try:
                    await update_transfer_pass_status(transfer_id, curr_date, credit)
                except Exception as ex:
                    try:
                        AppError.objects.create(
                            source='5',
                            error_type='6',
                            description=f'Не удалось обновить статус кредита в гугл таблицах (отправка денег, замена на "в кредит") {transfer_id}. {ex}',
                        )
                    except:
                        pass
                
                try:
                    await bot.send_message(chat_id=user_id,
                            text='Перевод помечен как выданный.',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='3',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            else:
                try:
                    await bot.send_message(chat_id=user_id,
                            text='Данные устарели.',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='3',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass


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

                if transfer.credit:
                    pass_date += f' (в кредит)'

                reply_text = f'''
                            *Отправитель:*\
                            \nИмя: *{sender.name}*\
                            \nНомер: *{sender.phone}*\
                            \nАдрес: *{sender_address}*\
                            \nСтатус в системе: *{delivery.status_message}*\
                            \n\
                            \n*Получатель:*\
                            \nКод: *{transfer.pk}*\
                            \nСумма: *{transfer.usd_amount} $*\
                            \nИмя: *{receiver.name}*\
                            \nНомер: *{receiver.phone}*\
                            \nДоставка: *{pick_up}*\
                            \nАдрес: *{receiver_address}*\
                            \nВыдано: *{pass_date}*\
                            '''
                
                status: Status = await sync_to_async(lambda: delivery.status)()
                if status.slug == 'finished' and pass_date == 'не выдано':
                    keyboard = await keyboards.pass_money_keyboard(transfer.pk)
                elif status.slug == 'api' and pass_date == 'не выдано':
                    keyboard = await keyboards.credit_money_keyboard(transfer.pk)
                else:
                    keyboard = InlineKeyboardBuilder().as_markup()

                try:
                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            reply_markup=keyboard,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='3',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            else:
                try:
                    await bot.send_message(chat_id=user_id,
                            text='Перевода с таким кодом не найдено.',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='3',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        else:
            try:
                await bot.send_message(chat_id=user_id,
                            text='Не похоже на код получателя, должно быть целое число.',
                            )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='3',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

                
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())