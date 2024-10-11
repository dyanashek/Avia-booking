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

from core.models import UsersSim, Notification, TGText, Language
from errors.models import AppError
from core.utils import create_icount_invoice
from drivers.models import Driver
from sim.models import Collect, Report

import config
import keyboards
import utils


bot = Bot(token=config.TELEGRAM_DRIVERS_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_message(message: types.Message):
    user_id = str(message.from_user.id)
    user = await sync_to_async(Driver.objects.filter(telegram_id=user_id).first)()
    if user:
        try:
            await bot.send_message(chat_id=user_id,
                            text='Привет.\nСюда будут приходить уведомления о денежных средствах за сим-карты.',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='2',
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

    user = await sync_to_async(Driver.objects.filter(telegram_id=user_id).first)()
    if user:
        curr_input = user.curr_input

        message_id = call.message.message_id
        chat_id = call.message.chat.id
        call_data = call.data.split('_')
        query = call_data[0]

        if query == 'pass':
            sim_id = int(call_data[1])
            sim = await sync_to_async(UsersSim.objects.filter(id=sim_id).first)()

            user.curr_input = None
            await sync_to_async(user.save)()

            if sim:
                sim.driver = user
                await sync_to_async(sim.save)()
            
            try:
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='2',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            try:
                await bot.send_message(chat_id=chat_id,
                        text='Клиента не передал денежных средств.',
                        parse_mode='Markdown',
                        )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='2',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        
        elif query == 'amount':
            sim_id = int(call_data[1])

            user.curr_input = f'amount_{sim_id}'
            await sync_to_async(user.save)()

            try:
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='2',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=chat_id,
                        text='Введите сумму в шекелях (₪), переданную клиентом.',
                        parse_mode='Markdown',
                        )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='2',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        
        elif query == 'retype':
            sim_id = int(call_data[1])

            user.curr_input = f'amount_{sim_id}'
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='2',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=chat_id,
                        text='Введите сумму в шекелях (₪), переданную клиентом.',
                        parse_mode='Markdown',
                        )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='2',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        
        elif query == 'confirm':
            info_type = call_data[1]

            if info_type == 'sim':
                amount = float(call_data[2])
                sim_id = int(call_data[3])

                sim = await sync_to_async(UsersSim.objects.filter(id=sim_id).first)()
                if sim:
                    sim.driver = user
                    sim.debt -= amount
                    await sync_to_async(sim.save)()

                    try:
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=InlineKeyboardBuilder().as_markup(),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='2',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass
                    
                    try:
                        collect = await sync_to_async(Collect.objects.filter(sim=sim, amount__isnull=True).first)()
                        if collect:
                            collect.amount = amount
                            await sync_to_async(collect.save)()

                            sim_collect_report, _ = await sync_to_async(Report.objects.get_or_create)(report_date=datetime.datetime.utcnow().date())
                            if collect.driver == '1':
                                sim_collect_report.first_driver_ils += amount
                                sim_collect_report.first_driver_points += 1
                            elif collect.driver == '2':
                                sim_collect_report.second_driver_ils += amount
                                sim_collect_report.second_driver_points += 1
                            elif collect.driver == '3':
                                sim_collect_report.third_driver_ils += amount
                                sim_collect_report.third_driver_points += 1
                            
                            await sync_to_async(sim_collect_report.save)()
                        else:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='2',
                                    error_type='10',
                                    main_user=user_id,
                                    description=f'Не удалось внести сумму собранную за симкарту в сущность забора и отчет. Сумма {amount}, телефон {sim.sim_phone}.',
                                )
                            except:
                                pass
                    except:
                        pass

                    invoice_url = await create_icount_invoice(sim.icount_id, amount, sim.is_old_sim)
                    if invoice_url:
                        sim_user = await sync_to_async(lambda: sim.user)()
                        user_language = await sync_to_async(lambda: sim_user.language)()
                        if not user_language:
                            user_language = await sync_to_async(Language.objects.get)(slug='rus')
                        invoice_text = await sync_to_async(TGText.objects.get)(slug='invoice_url', language=user_language)
                        reply_text = f'{invoice_text.text} {invoice_url}'
                        await sync_to_async(Notification.objects.create)(
                            user=sim_user,
                            text=reply_text,
                        )

                        try:
                            await bot.send_message(chat_id=chat_id,
                                text=f'Подтверждена передача клиентом суммы в {amount} ₪',
                                parse_mode='Markdown',
                                )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='2',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                    else:
                        sim.icount_collect_amount += amount
                        sim.icount_api_collect = False
                        await sync_to_async(sim.save)()

                        try:
                            await bot.send_message(chat_id=chat_id,
                                text=f'Подтверждена передача клиентом суммы в {amount} ₪. Квитанция не сформировалась, воспользуйтесь админ панелью.',
                                parse_mode='Markdown',
                                )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='2',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                else:
                    try:
                        await bot.send_message(chat_id=chat_id,
                                text=f'Ошибка подтверждения, попробуйте позднее.',
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='2',
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
    username = message.from_user.username
    chat_id = message.chat.id

    user = await sync_to_async(Driver.objects.filter(telegram_id=user_id).first)()
    curr_input = user.curr_input
    input_info = await utils.escape_markdown(message.text)

    if user:
        if curr_input and 'amount' in curr_input:
            user.curr_input = None
            await sync_to_async(user.save)()

            data = curr_input.split('_')
            sim_id = int(data[1])
            amount = round(await utils.validate_price(input_info), 2)

            if amount:
                try:
                    await bot.send_message(chat_id=user_id,
                                    text=f'Сумма, переданная клиентом: *{amount} ₪*?',
                                    reply_markup=await keyboards.confirm_amount_keyboard(amount, sim_id),
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='2',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            else:
                try:
                    await bot.send_message(chat_id=user_id,
                                    text='Не похоже на корректную сумму, введите сумму в шекелях еще раз.',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='2',
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