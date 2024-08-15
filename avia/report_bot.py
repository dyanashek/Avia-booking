import os
import datetime

import django
from django.db.models.functions import TruncDate
import calendar

import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from money_transfer.models import Delivery, Transfer, Manager, BuyRate, DebitCredit, Balance, Operation_types

import config
import keyboards
import utils


bot = Bot(token=config.TELEGRAM_REPORT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_message(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in config.REPORT_MANAGER_ID:
        user, created = await sync_to_async(Manager.objects.get_or_create)(telegram_id=user_id)
        if not created:
            user.curr_input = None
            await sync_to_async(user.save)()

        await bot.send_message(chat_id=user_id,
                        text='Выберите один из вариантов:',
                        reply_markup=await keyboards.data_or_report_keyboard(),
                        )
    else:
        await bot.send_message(chat_id=user_id,
                        text='Нет доступа, обратитесь к администратору.',
                        )


@dp.message(Command("cancel"))
async def cancel_message(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id in config.REPORT_MANAGER_ID:
        user = await sync_to_async(Manager.objects.get)(telegram_id=user_id)
        user.curr_input = None
        await sync_to_async(user.save)()

        await bot.send_message(chat_id=user_id,
                        text='Ввод отменен.',
                        )


@dp.callback_query()
async def callback_query(call: types.CallbackQuery):
    """Handles queries from inline keyboards."""

    user_id = str(call.from_user.id)
    if user_id in config.REPORT_MANAGER_ID:
        user = await sync_to_async(Manager.objects.get)(telegram_id=user_id)
        curr_input = user.curr_input

        message_id = call.message.message_id
        chat_id = call.message.chat.id
        call_data = call.data.split('_')
        query = call_data[0]

        if query == 'report':
            report_type = call_data[1]
            if report_type == 'choose':
                await bot.edit_message_text(chat_id=chat_id,
                                                message_id=message_id,
                                                text='Выберите вариант отчета:',
                                                reply_markup=await keyboards.report_type_keyboard(),
                                                )
            elif report_type == 'input':
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                user.curr_input = 'report-date'
                await sync_to_async(user.save)()

                await bot.send_message(
                                chat_id=user_id,
                                text='Введите дату начала формирования отчета в формате дд.мм.гггг',
                                )

            elif report_type == 'balance':
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                balance = await sync_to_async(Balance.objects.get)(id=1)

                reply_text = f'''
                            *Текущие балансы:*\
                            \nДолг перед Равшаном: *{balance.debt_ravshan} $*\
                            \nДолг перед фирмами: *{balance.debt_firms} $*\
                            \nОстаток в Самарканде: *{balance.balance} $*\
                            '''
                
                await bot.send_message(
                                chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )

            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                curr_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()
                balance = await sync_to_async(Balance.objects.get)(id=1)
                if report_type == 'year':
                    year = curr_date.year
                    start = datetime.date(year=year, month=1, day=1)
                    end = datetime.date(year=year, month=12, day=31)

                elif report_type == 'month':
                    year = curr_date.year
                    month = curr_date.month

                    _, days_in_month = calendar.monthrange(year, month)

                    start = datetime.date(year=year, month=month, day=1)
                    end = datetime.date(year=year, month=month, day=days_in_month)

                elif report_type == 'day':
                    start = curr_date
                    end = curr_date

                await bot.send_message(
                                chat_id=user_id,
                                text='Отчет формируется...',
                                )

                report_data = await sync_to_async(Delivery.calculate_params)(start, end)
                
                if start == end:
                    period = start.strftime('%d.%m.%Y')
                else:
                    start = start.strftime('%d.%m.%Y')
                    end = end.strftime('%d.%m.%Y')
                    period = f'{start} - {end}'
                
                reply_text = f'''
                            *Текущие балансы:*\
                            \nДолг перед Равшаном: *{balance.debt_ravshan} $*\
                            \nДолг перед фирмами: *{balance.debt_firms} $*\
                            \nОстаток в Самарканде: *{balance.balance} $*\
                            \n\
                            \n*{period}:*\
                            \nПрибыль: *{report_data[0]} ₪*\
                            \nОборот брутто: *{report_data[1]} $*\
                            \nОборот нетто: *{report_data[2]} $*\
                            \nНесобранные: *{report_data[3]} $*\
                            \nНевыданные: *{report_data[4]} $*\
                            '''
                
                await bot.send_message(
                                chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )

        elif query == 'data':
            data_type = call_data[1]

            if data_type == 'choose':
                await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text='Выберите данные, которые хотите внести:',
                                            reply_markup=await keyboards.data_type_keyboard(),
                                            )
            else:
                if data_type == 'all':
                    data_text = '(все данные)'
                elif data_type == '1':
                    data_text = '(передано фирмам)'
                elif data_type == '2':
                    data_text = '(передано Равшану)'
                elif data_type == '3':
                    data_text = '(получено от фирм)'
                elif data_type == '4':
                    data_text = '(получено от Равшана)'
                elif data_type == 'rate':
                    data_text = '(курс покупки)'
                
                await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=f'Выберите дату, за которую вносятся данные *{data_text}*:',
                                            parse_mode='Markdown',
                                            reply_markup=await keyboards.data_date_keyboard(data_type),
                                            )
        
        elif query == 'date':
            data_type = call_data[1]
            date_text = call_data[2]

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            if date_text == 'input':
                user.curr_input = f'datefor_{data_type}'
                await sync_to_async(user.save)()

                await bot.send_message(chat_id=user_id,
                        text=f'Введите дату в формате "дд.мм.гггг".',
                        parse_mode="Markdown",
                        )

            else:
                date = datetime.datetime.strptime(date_text, '%d.%m.%Y').date()
                if data_type == 'all':
                    user.curr_input = f'all_1_{date_text}'
                    buy_rate = await sync_to_async(BuyRate.objects.filter(date=date).first)()
                    debits_credits = await sync_to_async(lambda: list(DebitCredit.objects.filter(date=date)))()
                    
                    await bot.send_message(chat_id=user_id,
                        text=f'Введите сумму в $ за *{date_text}* "передано фирмам".',
                        parse_mode="Markdown",
                        )

                    if buy_rate or debits_credits:
                        alert_text = f'{date_text}:'
                        if buy_rate:
                            alert_text += f'\n\nКурс: {buy_rate.rate}.'
                        if debits_credits:
                            for debit_credit in debits_credits:
                                data_type_text = ''
                                for operation_type in Operation_types:
                                    if operation_type[0] == debit_credit.operation_type:
                                        data_type_text = operation_type[1]
                                        alert_text += f'\n"{data_type_text}": {int(debit_credit.amount)}$.'
                                        break
                                
                        alert_text += '\n\nПри продолжении данные будут перезаписаны. Для отмены /cancel.'

                        await bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=alert_text,
                                show_alert=True,
                                )

                elif data_type == 'rate':
                    buy_rate = await sync_to_async(BuyRate.objects.filter(date=date).first)()

                    await bot.send_message(chat_id=user_id,
                        text=f'Введите курс покупки за *{date_text}*.',
                        parse_mode="Markdown",
                        )

                    if buy_rate:
                        await bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=f'За {date_text} ужe задан курс {buy_rate.rate}.\n\nПри продолжении данные будут перезаписаны.\n\nДля отмены воспользуйтесь командой /cancel.',
                                show_alert=True,
                                )
                    user.curr_input = f'rate_{date_text}'
                else:
                    data_type = int(data_type)

                    data_type_text = ''
                    for operation_type in Operation_types:
                        if operation_type[0] == data_type:
                            data_type_text = operation_type[1]
                            break

                    debit_credit = await sync_to_async(DebitCredit.objects.filter(date=date, operation_type=data_type).first)()

                    await bot.send_message(chat_id=user_id,
                                            text=f'Введите сумму в $ за *{date_text}* "{data_type_text}".',
                                            parse_mode="Markdown",
                                            )

                    if debit_credit:
                        await bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=f'За {date_text} ужe существует операция "{data_type_text}" со значением {int(debit_credit.amount)}$.\n\nПри продолжении данные будут перезаписаны.\n\nДля отмены воспользуйтесь командой /cancel.',
                                show_alert=True,
                                )

                    user.curr_input = f'{data_type}_{date_text}'

                await sync_to_async(user.save)()

        elif query == 'db':
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            debits_credits = await sync_to_async(lambda: list(DebitCredit.objects.all()))()
            debits_credits = debits_credits[:20]
            buy_rates = await sync_to_async(lambda: list(BuyRate.objects.all()))()
            buy_rates = buy_rates[:20]

            reply_text = '*Дебит-кредит*:\n'
            for debit_credit in debits_credits:
                date_text = debit_credit.date.strftime('%d.%m.%Y')
                date_type_text = ''

                for operation_type in Operation_types:
                    if operation_type[0] == debit_credit.operation_type:
                        date_type_text = operation_type[1]
                        break
                
                reply_text += f'*{date_text}*: {date_type_text} {int(debit_credit.amount)}$\n'
            
            reply_text += '\n*Курсы:*\n'

            for buy_rate in buy_rates:
                date_text = buy_rate.date.strftime('%d.%m.%Y')
                reply_text += f'*{date_text}:* {buy_rate.rate}\n'

            await bot.send_message(chat_id=user_id,
                        text=reply_text,
                        parse_mode='Markdown',
                        )

        elif query == 'missing':
            unique_dates = await sync_to_async(lambda: list(Delivery.objects.annotate(date=TruncDate('created_at')).values('date').distinct()))()
            
            reply_text = '*Отсутствуют курсы покупки за следующие даты:*\n'

            for unique_date in unique_dates:
                unique_date = unique_date['date']
                buy_rate = await sync_to_async(BuyRate.objects.filter(date=unique_date).first)()
                if not buy_rate:
                    unique_date = unique_date.strftime('%d.%m.%Y')
                    reply_text += f'{unique_date}, '
            
            reply_text = reply_text.rstrip(', ')

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            await bot.send_message(chat_id=user_id,
                        text=reply_text,
                        parse_mode='Markdown',
                        )

        elif query == 'back':
            destination = call_data[1]

            if destination == 'main':
                await bot.edit_message_text(chat_id=user_id,
                                            message_id=message_id,
                                            text='Выберите один из вариантов:',
                                            reply_markup=await keyboards.data_or_report_keyboard(),
                                            )         

            elif destination == 'data':
                await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text='Выберите данные, которые хотите внести:',
                                            reply_markup=await keyboards.data_type_keyboard(),
                                            )
            
            elif destination == 'report':
                await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text='Выберите вариант отчета:',
                                            reply_markup=await keyboards.report_type_keyboard(),
                                            )


@dp.message(F.text)
async def handle_text(message):
    """Handles message with type text."""
    user_id = str(message.from_user.id)
    if user_id in config.REPORT_MANAGER_ID:
        username = message.from_user.username

        user = await sync_to_async(Manager.objects.get)(telegram_id=user_id)
        curr_input = user.curr_input

        input_info = await utils.escape_markdown(message.text)

        if curr_input and 'report-date' in curr_input:
            input_data = curr_input.split('_')
            if len(input_data) == 1:
                date_start = await utils.validate_date(input_info)
                if date_start:
                    date_start_text = date_start.strftime('%d.%m.%Y')
                    user.curr_input += f'_{date_start_text}'
                    await sync_to_async(user.save)()

                    await bot.send_message(
                                chat_id=user_id,
                                text='Введите дату окончания формирования отчета в формате дд.мм.гггг',
                                )
                else:
                    await bot.send_message(chat_id=user_id,
                                            text=f'Не похоже на дату, попробуйте еще раз.\nВведите дату в формате "дд.мм.гггг"',
                                            parse_mode="Markdown",
                                            )
            
            elif len(input_data) == 2:
                end = await utils.validate_date(input_info)
                if end:
                    user.curr_input = None
                    await sync_to_async(user.save)()

                    start = datetime.datetime.strptime(input_data[1], '%d.%m.%Y')
                    balance = await sync_to_async(Balance.objects.get)(id=1)

                    await bot.send_message(
                                chat_id=user_id,
                                text='Отчет формируется...',
                                )

                    report_data = await sync_to_async(Delivery.calculate_params)(start, end)
                
                    if start == end:
                        period = start.strftime('%d.%m.%Y')
                    else:
                        start = start.strftime('%d.%m.%Y')
                        end = end.strftime('%d.%m.%Y')
                        period = f'{start} - {end}'
                    
                    reply_text = f'''
                                *Текущие балансы:*\
                                \nДолг перед Равшаном: *{balance.debt_ravshan} $*\
                                \nДолг перед фирмами: *{balance.debt_firms} $*\
                                \nОстаток в Самарканде: *{balance.balance} $*\
                                \n\
                                \n*{period}:*\
                                \nПрибыль: *{report_data[0]} ₪*\
                                \nОборот брутто: *{report_data[1]} $*\
                                \nОборот нетто: *{report_data[2]} $*\
                                \nНесобранные: *{report_data[3]} $*\
                                \nНевыданные: *{report_data[4]} $*\
                                '''
                    
                    await bot.send_message(
                                    chat_id=user_id,
                                    text=reply_text,
                                    parse_mode='Markdown',
                                    )

                else:
                    await bot.send_message(chat_id=user_id,
                                            text=f'Не похоже на дату, попробуйте еще раз.\nВведите дату в формате "дд.мм.гггг"',
                                            parse_mode="Markdown",
                                            )
            
           
                
            
        elif curr_input and 'datefor' in curr_input:
            date = await utils.validate_date(input_info)
            if date:
                data_type = curr_input.split('_')[1]
                date_text = date.strftime('%d.%m.%Y')

                if data_type == 'all':
                    user.curr_input = f'all_1_{date_text}'
                    buy_rate = await sync_to_async(BuyRate.objects.filter(date=date).first)()
                    debits_credits = await sync_to_async(lambda: list(DebitCredit.objects.filter(date=date)))()

                    if buy_rate or debits_credits:
                        alert_text = f'{date_text}:'
                        if buy_rate:
                            alert_text += f'\n\nКурс: {buy_rate.rate}.'
                        if debits_credits:
                            for debit_credit in debits_credits:
                                data_type_text = ''
                                for operation_type in Operation_types:
                                    if operation_type[0] == debit_credit.operation_type:
                                        data_type_text = operation_type[1]
                                        alert_text += f'\n"{data_type_text}": {int(debit_credit.amount)}$.'
                                        break
                        
                        alert_text += '\n\nПри продолжении данные будут перезаписаны. Для отмены /cancel.'

                        await bot.send_message(
                                chat_id=user_id,
                                text=alert_text,
                                )
                    
                    await bot.send_message(chat_id=user_id,
                        text=f'Введите сумму в $ за *{date_text}* "передано фирмам".',
                        parse_mode="Markdown",
                        )

                elif data_type == 'rate':
                    buy_rate = await sync_to_async(BuyRate.objects.filter(date=date).first)()

                    if buy_rate:
                        await bot.send_message(
                                chat_id=user_id,
                                text=f'За {date_text} ужe задан курс {buy_rate.rate}.\n\nПри продолжении данные будут перезаписаны.\n\nДля отмены воспользуйтесь командой /cancel.',
                                )
                    
                    await bot.send_message(chat_id=user_id,
                        text=f'Введите курс покупки за *{date_text}*.',
                        parse_mode="Markdown",
                        )

                    user.curr_input = f'rate_{date_text}'

                else:
                    data_type = int(data_type)

                    data_type_text = ''
                    for operation_type in Operation_types:
                        if operation_type[0] == data_type:
                            data_type_text = operation_type[1]
                            break

                    debit_credit = await sync_to_async(DebitCredit.objects.filter(date=date, operation_type=data_type).first)()

                    if debit_credit:
                        await bot.send_message(
                                chat_id=user_id,
                                text=f'За {date_text} ужe существует операция "{data_type_text}" со значением {int(debit_credit.amount)}$.\n\nПри продолжении данные будут перезаписаны.\n\nДля отмены воспользуйтесь командой /cancel.',
                                )
                    
                    await bot.send_message(chat_id=user_id,
                                            text=f'Введите сумму в $ за *{date_text}* "{data_type_text}".',
                                            parse_mode="Markdown",
                                            )

                    user.curr_input = f'{data_type}_{date_text}'
                    
                await sync_to_async(user.save)()

            else:
                await bot.send_message(chat_id=user_id,
                                        text=f'Не похоже на дату, попробуйте еще раз.\nВведите дату в формате "дд.мм.гггг"',
                                        parse_mode="Markdown",
                                        )

        elif curr_input and 'all' in curr_input:
            data_input_info = curr_input.split('_')
            date_text = data_input_info[2]
            date = datetime.datetime.strptime(data_input_info[2], '%d.%m.%Y')

            if 'rate' in curr_input:
                curr_rate = await utils.validate_rate(input_info)
                if curr_rate:
                    user.curr_input = None
                    await sync_to_async(user.save)()

                    data_input_info = curr_input.split('_')

                    buy_rate, _ = await sync_to_async(BuyRate.objects.get_or_create)(date=date)
                    buy_rate.rate = curr_rate
                    await sync_to_async(buy_rate.save)()

                    await bot.send_message(chat_id=user_id,
                                            text=f'Данные сохранены',
                                            )
                else:
                    await bot.send_message(chat_id=user_id,
                                            text=f'Не похоже на курс, введите еще раз.\nДолжен быть дробным числом, например 3.7.',
                                            parse_mode="Markdown",
                                            )

            else:
                curr_amount = await utils.validate_price(input_info)
                
                if curr_amount:
                    data_type = int(data_input_info[1])
                    data_input_info = curr_input.split('_')

                    debit_credit, created = await sync_to_async(DebitCredit.objects.get_or_create)(date=date, operation_type=data_type)

                    if not created:
                        prev_amount = debit_credit.amount

                    debit_credit.amount = curr_amount
                    await sync_to_async(debit_credit.save)()

                    balance = await sync_to_async(Balance.objects.get)(id=1)
                    if data_type == 1:
                        if not created:
                            balance.debt_firms += prev_amount

                        user.curr_input = f'all_2_{date_text}'
                        balance.debt_firms -= curr_amount

                        await bot.send_message(chat_id=user_id,
                                            text=f'Введите сумму в $ за *{date_text}* "передано Равшану".',
                                            parse_mode="Markdown",
                                            )

                    elif data_type == 2:
                        if not created:
                            balance.debt_ravshan += prev_amount

                        user.curr_input = f'all_3_{date_text}'
                        balance.debt_ravshan -= curr_amount

                        await bot.send_message(chat_id=user_id,
                                            text=f'Введите сумму в $ за *{date_text}* "получено от фирм".',
                                            parse_mode="Markdown",
                                            )

                    elif data_type == 3:
                        if not created:
                            balance.debt_firms -= prev_amount
                            balance.balance -= prev_amount

                        user.curr_input = f'all_4_{date_text}'
                        balance.debt_firms += curr_amount
                        balance.balance += curr_amount

                        await bot.send_message(chat_id=user_id,
                                            text=f'Введите сумму в $ за *{date_text}* "получено от Равшана".',
                                            parse_mode="Markdown",
                                            )

                    elif data_type == 4:
                        if not created:
                            balance.debt_ravshan -= prev_amount
                            balance.balance -= prev_amount

                        user.curr_input = f'all_rate_{date_text}'
                        balance.debt_ravshan += curr_amount
                        balance.balance += curr_amount

                        await bot.send_message(chat_id=user_id,
                                            text=f'Введите курс покупки за *{date_text}*.',
                                            parse_mode="Markdown",
                                            )
                    
                    await sync_to_async(user.save)()
                    await sync_to_async(balance.save)()

                else:
                    await bot.send_message(chat_id=user_id,
                                            text=f'Не похоже на корректную сумму, введите еще раз.\nДолжна быть дробным или целым числом, например: 1000.',
                                            )

        elif curr_input and 'rate' in curr_input:
            curr_rate = await utils.validate_rate(input_info)
            if curr_rate:
                user.curr_input = None
                await sync_to_async(user.save)()

                data_input_info = curr_input.split('_')
                date = datetime.datetime.strptime(data_input_info[1], '%d.%m.%Y')

                buy_rate, _ = await sync_to_async(BuyRate.objects.get_or_create)(date=date)
                buy_rate.rate = curr_rate
                await sync_to_async(buy_rate.save)()

                await bot.send_message(chat_id=user_id,
                                        text=f'Данные сохранены.',
                                        )
            else:
                await bot.send_message(chat_id=user_id,
                                        text=f'Не похоже на курс, введите еще раз.\nДолжен быть дробным числом, например 3.7.',
                                        parse_mode="Markdown",
                                        )

        elif curr_input:
            curr_amount = await utils.validate_price(input_info)
            if curr_amount:
                user.curr_input = None
                await sync_to_async(user.save)()

                data_input_info = curr_input.split('_')
                data_type = int(data_input_info[0])
                date = datetime.datetime.strptime(data_input_info[1], '%d.%m.%Y')

                debit_credit, created = await sync_to_async(DebitCredit.objects.get_or_create)(date=date, operation_type=data_type)

                if not created:
                    prev_amount = debit_credit.amount
                
                debit_credit.amount = curr_amount
                await sync_to_async(debit_credit.save)()

                await bot.send_message(chat_id=user_id,
                                        text=f'Данные сохранены',
                                        )

                balance = await sync_to_async(Balance.objects.get)(id=1)
                if data_type == 1:
                    if not created:
                        balance.debt_firms += prev_amount

                    balance.debt_firms -= curr_amount
                elif data_type == 2:
                    if not created:
                        balance.debt_ravshan += prev_amount

                    balance.debt_ravshan -= curr_amount
                elif data_type == 3:
                    if not created:
                        balance.debt_firms -= prev_amount
                        balance.balance -= prev_amount

                    balance.debt_firms += curr_amount
                    balance.balance += curr_amount
                elif data_type == 4:
                    if not created:
                        balance.debt_ravshan -= prev_amount
                        balance.balance -= prev_amount

                    balance.debt_ravshan += curr_amount
                    balance.balance += curr_amount

                await sync_to_async(balance.save)()

            else:
                await bot.send_message(chat_id=user_id,
                                        text=f'Не похоже на корректную сумму, введите еще раз.\nДолжна быть дробным или целым числом, например: 1000.',
                                        )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())