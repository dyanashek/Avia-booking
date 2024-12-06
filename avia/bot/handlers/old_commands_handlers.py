import os
import datetime
import django

from aiogram import Router
from aiogram import types
from aiogram.filters.command import Command, CommandObject

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from django.db.models import Q

from core.models import TGUser, TGText, Language, Parcel, Flight, UsersSim
from money_transfer.models import Delivery
from errors.models import AppError
from sim.models import SimCard

import config
import keyboards
import utils
from filters import ChatTypeFilter


router = Router()


@router.message(ChatTypeFilter(chat_type='private'), Command("start"))
async def start_message(message: types.Message, command: CommandObject):
    '''Handles start command.'''
    user_id = str(message.from_user.id)
    username = message.from_user.username
    if not username:
        username = None

    user, _ = await sync_to_async(TGUser.objects.get_or_create)(user_id=user_id)
    user.username = username
    user.active = True
    user.curr_input = None
    await sync_to_async(user.save)()

    if command.args:
        if 'money' in command.args:
            try:
                delivery_id = int(command.args.replace('money', ''))
                delivery = await sync_to_async(Delivery.objects.get)(id=delivery_id)
            except:
                delivery = None

            if delivery:
                delivery_sender = await sync_to_async(lambda: delivery.sender)()
                delivery_user = await sync_to_async(lambda: delivery_sender.user)()
                if delivery.approved_by_client is None and (delivery_user is None or delivery_user.user_id == user_id):
                    if delivery_user is None:
                        delivery_sender.user = user
                        await sync_to_async(delivery_sender.save)(update_fields=['user'])

                    reply_message = f'''
                                \nПодтвердите информацию о переводе!\
                                \n\
                                \n*Отправление:*\
                                \nНомер отправителя: *{delivery_sender.phone}*\
                                '''
                    if delivery.ils_amount:
                        reply_message += f'\nСумма в ₪: *{int(delivery.ils_amount)}*'
                    
                    reply_message += f'''\nСумма в $: *{int(delivery.usd_amount)}*\
                                \nКомиссия в ₪: *{int(delivery.commission)}*\
                                '''

                    if delivery.ils_amount:     
                        reply_message += f'Итого в $: *{int(delivery.total_usd)}*'
                    
                    reply_message += f'\n\n*Получатели:*'

                    transfers = await sync_to_async(lambda: list(delivery.transfers.all()))()
                    for num, transfer in enumerate(transfers):
                        if transfer.pick_up:
                            pick_up = 'да'
                        else:
                            pick_up = 'нет'

                        receiver = await sync_to_async(lambda: transfer.receiver)()
                        transfer_message = f'''\n{num + 1}. Код получения: *{transfer.id}*\
                                            \nНомер получателя: *{receiver.phone}*\
                                            \nСумма: *{int(transfer.usd_amount)} $*\
                                            \nДоставка: *{pick_up}*\
                                            '''
                        
                        address = await sync_to_async(lambda: transfer.address)()
                        if address:
                            transfer_message += f'\nАдрес: *{address.address}*'
                        transfer_message += '\n'
                        reply_message += transfer_message
                    
                    
                    try:
                        await message.answer(
                            text=reply_message, 
                            parse_mode='Markdown',
                            )

                        return

                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение с подтверждением денежного перевода пользователю {user_id} после перехода по ссылке с параметром',
                            )
                        except:
                            pass

        else:
            phone_number = await utils.extract_digits(command.args)
            if phone_number:
                user_sim = await sync_to_async(UsersSim.objects.filter(user=user).first)()
                if not user_sim:
                    admin_sim = await sync_to_async(SimCard.objects.filter(
                        Q(icount_api=True) & 
                        Q(to_main_bot=False) & 
                        Q(sim_phone=phone_number)).first)()
                    
                    if admin_sim:
                        fare = await sync_to_async(lambda: admin_sim.fare)()
                        users_sim = UsersSim(
                            user=user,
                            fare=fare,
                            sim_phone=admin_sim.sim_phone,
                            next_payment=admin_sim.next_payment,
                            debt=admin_sim.debt,
                            icount_id=admin_sim.icount_id,
                            icount_api=True,
                            is_old_sim=True,
                            is_stopped=admin_sim.is_stopped,
                        )

                        await sync_to_async(users_sim.save)()
                        admin_sim.to_main_bot = True
                        await sync_to_async(admin_sim.save)()

                        if users_sim.debt >= config.SIM_DEBT_LIMIT:
                            users_sim.pay_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()
                            language = await sync_to_async(lambda: user.language)()
                            if not language:
                                language = await sync_to_async(Language.objects.get)(slug='rus')

                            sim_debt = await sync_to_async(TGText.objects.get)(slug='sim_debt', language=language)
                            fare_text = await sync_to_async(TGText.objects.get)(slug='fare', language=language)
                            fare_price_text = await sync_to_async(TGText.objects.get)(slug='fare_price', language=language)
                            payment_needed = await sync_to_async(TGText.objects.get)(slug='payment_needed', language=language)

                            reply_message = f'''
                                {sim_debt.text} {users_sim.sim_phone}:\
                                \n*{users_sim.debt} ₪*\
                                \n\
                                \n*{fare_text.text}*\
                                \n{fare.description}\
                                \n*{fare_price_text.text} {fare.price}₪*\
                                \n\
                                \n{payment_needed.text}\
                                '''
                            
                            try:
                                await message.answer(
                                    text=reply_message,
                                    reply_markup=await keyboards.ready_pay_keyboard(language),
                                    parse_mode='Markdown',
                                )
                                users_sim.notified = True
                                await sync_to_async(users_sim.save)()

                                return

                            except:
                                try:
                                    await sync_to_async(AppError.objects.create)(
                                        source='1',
                                        error_type='2',
                                        main_user=user_id,
                                        description=f'Не удалось отправить сообщение о готовности оплаты пользователю {user_id} после перехода по ссылке для привязки номера телефона.)',
                                    )
                                except:
                                    pass

    await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
    await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

    user_language = await sync_to_async(lambda: user.language)()
    if user_language:
        reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)
        try:
            await message.answer(
                                text=reply_text.text,
                                reply_markup=await keyboards.flight_or_parcel_keyboard(user_language),
                                parse_mode='Markdown',
                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение c выбором опций пользователю {user_id}.)',
                )
            except:
                pass
    else:
        choose_language = await sync_to_async(TGText.objects.get)(slug='choose_language')

        try:
            await message.answer(text=choose_language.text,
                            reply_markup=await keyboards.choose_language_keyboard(),
                            parse_mode='Markdown',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение с выбором языка пользователю {user_id}.',
                )
            except:
                pass


@router.message(ChatTypeFilter(chat_type='private'), Command("language"))
async def language_message(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    if not username:
        username = None

    user, _ = await sync_to_async(TGUser.objects.get_or_create)(user_id=user_id)
    user.username = username
    user.curr_input = None
    await sync_to_async(user.save)()

    await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
    await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

    choose_language = await sync_to_async(TGText.objects.get)(slug='choose_language')

    try:
        await message.answer(text=choose_language.text,
                            reply_markup=await keyboards.choose_language_keyboard(),
                            parse_mode='Markdown',
                            )
    except:
        try:
            await sync_to_async(AppError.objects.create)(
                source='1',
                error_type='2',
                main_user=user_id,
                description=f'Не удалось отправить сообщение с выбором языка пользователю {user_id}.',
            )
        except:
            pass


@router.message(ChatTypeFilter(chat_type='private'), Command("getid"))
async def id_message(message: types.Message):
    try:
        await message.reply(
            text=f'*Telegram ID:* {message.from_user.id}',
            parse_mode='Markdown',
        )
    except:
        try:
            await sync_to_async(AppError.objects.create)(
                source='1',
                error_type='2',
                main_user=message.from_user.id,
                description=f'Не удалось отправить id пользователю {message.from_user.id}.',
            )
        except:
            pass
