import os
import datetime
import uuid

import django

import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from django.core.files.base import ContentFile
from filer.models import Image, Folder
from django.db.models import Q

from core.models import (TGUser, TGText, Language, Parcel, Flight, Route, Day, ParcelVariation, SimFare, 
                         UsersSim, UserMessage, Notification)
from errors.models import AppError
from core.utils import (send_pickup_address, send_sim_delivery_address, send_sim_money_collect_address,
                        create_icount_client, get_address,)
from sim.models import SimCard

import config
import keyboards
import functions
import utils
from filters import ChatTypeFilter


bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher()


@dp.message(ChatTypeFilter(chat_type='private'), Command("start"))
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

                        message = f'''
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
                            await bot.send_message(
                                chat_id=user_id,
                                text=message,
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
            await bot.send_message(chat_id=user_id,
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
            await bot.send_message(chat_id=user_id,
                            text=choose_language.text,
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


@dp.message(ChatTypeFilter(chat_type='private'), Command("language"))
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
        await bot.send_message(chat_id=user_id,
                            text=choose_language.text,
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


@dp.callback_query()
async def callback_query(call: types.CallbackQuery):
    """Handles queries from inline keyboards."""

    # getting message's and user's ids
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    user_id = str(call.from_user.id)
    username = call.from_user.username

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')
    curr_input = user.curr_input

    if username:
        user.username = username
        await sync_to_async(user.save)()
    
    call_data = call.data.split('_')
    query = call_data[0]

    if query == 'language':
        await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
        await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

        language_id = int(call_data[1])
        language = await sync_to_async(Language.objects.get)(id=language_id)
        user.language = language
        await sync_to_async(user.save)()

        welcome_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=language)

        try:
            await call.message.edit_text(text=welcome_text.text,
                                        reply_markup=await keyboards.flight_or_parcel_keyboard(language),
                                        parse_mode='Markdown',
                                        )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass
    
    elif query == 'flight':
        await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
        await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

        flight = Flight(user=user)
        await sync_to_async(flight.save)()
        user.curr_input = 'flight_route'
        await sync_to_async(user.save)()

        choose_route = await sync_to_async(TGText.objects.get)(slug='choose_route', language=user_language)

        try:
            await call.message.edit_text(text=choose_route.text,
                                        reply_markup=await keyboards.route_keyboard(),
                                        parse_mode='Markdown',
                                        )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass

    elif query == 'route':
        route_id = int(call_data[1])
        route = await sync_to_async(Route.objects.filter(id=route_id).first)()
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()

        if route and flight and curr_input and curr_input == 'flight_route':
            flight.route = route
            await sync_to_async(flight.save)()
            user.curr_input = 'flight_type'
            await sync_to_async(user.save)()

            choose_flight_type = await sync_to_async(TGText.objects.get)(slug='choose_options', language=user_language)
            try:
                await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=choose_flight_type.text,
                                        parse_mode='Markdown',
                                        )
                
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=await keyboards.flight_type_keyboard(user_language),
                                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif query == 'flighttype':
        flight_type = call_data[1]
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        if flight and curr_input and curr_input == 'flight_type':
            flight.type = flight_type
            await sync_to_async(flight.save)()
            user.curr_input = 'flight_departure'
            await sync_to_async(user.save)()

            departure_text = await sync_to_async(TGText.objects.get)(slug='choose_departure_month', language=user_language)
            try:
                await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=departure_text.text,
                                        parse_mode='Markdown',
                                        )
                
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year, user_language),
                                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
    
    elif query == 'month':
        direction = call_data[1]
        year = int(call_data[2])
        month = int(call_data[3])

        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        if flight and direction == 'departure' and curr_input and curr_input == 'flight_departure':
            departure_days = await sync_to_async(lambda: list(flight.route.days.filter(Q(day__year=year) & Q(day__month=month) & Q(day__gte=datetime.date.today()))))()
            if departure_days:
                departure_day = await sync_to_async(TGText.objects.get)(slug='choose_departure_day', language=user_language)
                try:
                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=departure_day.text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.choose_day_keyboard(departure_days, user_language),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

            else:
                no_flight = await sync_to_async(TGText.objects.get)(slug='no_flights', language=user_language)
                try:
                    await bot.answer_callback_query(
                                    callback_query_id=call.id,
                                    text=no_flight.text,
                                    show_alert=True,
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        elif flight and direction == 'arrival' and curr_input and curr_input == 'flight_arrival':
            arrival_days = await sync_to_async(lambda: list(flight.route.opposite.days.filter(Q(day__year=year) & Q(day__month=month) & Q(day__gte=datetime.date.today()))))()
            if arrival_days:
                arrival_day = await sync_to_async(TGText.objects.get)(slug='choose_arrival_day', language=user_language)
                try:
                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=arrival_day.text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.choose_day_keyboard(arrival_days, user_language, 'arrival'),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

            else:
                no_flight = await sync_to_async(TGText.objects.get)(slug='no_flights', language=user_language)
                try:
                    await bot.answer_callback_query(
                                    callback_query_id=call.id,
                                    text=no_flight.text,
                                    show_alert=True,
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif query == 'day':
        direction = call_data[1]
        date_id = int(call_data[2])
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        if flight and direction == 'departure' and curr_input and curr_input == 'flight_departure':
            flight_departure_date_db = await sync_to_async(Day.objects.filter(id=date_id).first)()
            flight.departure_date = flight_departure_date_db.day
            await sync_to_async(flight.save)()
            if flight.type == 'roundtrip':
                user.curr_input = 'flight_arrival'
                await sync_to_async(user.save)()

                arrival_text = await sync_to_async(TGText.objects.get)(slug='choose_arrival_month', language=user_language)
                try:
                    await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=arrival_text.text,
                                            parse_mode='Markdown',
                                            )
                    
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year, user_language, 'arrival'),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

            elif flight.type == 'oneway':
                user.curr_input = 'passport'
                await sync_to_async(user.save)()

                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
                user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                    reuse = await sync_to_async(TGText.objects.get)(slug='reuse', language=user_language)
                    name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                    family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                    passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                    sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                    birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                    start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                    end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                    phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                    address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                    reply_text = f'{reuse.text}\n'
                    
                    reply_text += f'\n*{name.text}* {user.name}'
                    reply_text += f'\n*{family_name.text}* {user.family_name}'
                    reply_text += f'\n*{passport.text}* {user.passport_number}'
                    reply_text += f'\n*{sex.text}* {user.sex}'
                    reply_text += f'\n*{birth_date.text}* {user.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {user.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {user.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {user.phone}'
                    reply_text += f'\n*{address.text}* {user.addresses}'

                    try:
                        await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=user.passport_photo_id,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

                else:
                    passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=passport_request.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass
                
        elif flight and direction == 'arrival' and curr_input and curr_input == 'flight_arrival':
            day = await sync_to_async(Day.objects.filter(id=date_id).first)()
            flight.arrival_date = day.day
            await sync_to_async(flight.save)()
            user.curr_input = 'passport'
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
                user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                reuse = await sync_to_async(TGText.objects.get)(slug='reuse', language=user_language)
                name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                reply_text = f'{reuse.text}\n'
                
                reply_text += f'\n*{name.text}* {user.name}'
                reply_text += f'\n*{family_name.text}* {user.family_name}'
                reply_text += f'\n*{passport.text}* {user.passport_number}'
                reply_text += f'\n*{sex.text}* {user.sex}'
                reply_text += f'\n*{birth_date.text}* {user.birth_date.strftime("%d.%m.%Y")}'
                reply_text += f'\n*{start_date.text}* {user.start_date.strftime("%d.%m.%Y")}'
                reply_text += f'\n*{end_date.text}* {user.end_date.strftime("%d.%m.%Y")}'
                reply_text += f'\n*{phone.text}* {user.phone}'
                reply_text += f'\n*{address.text}* {user.addresses}'

                try:
                    await bot.send_photo(chat_id=user_id,
                            caption=reply_text,
                            photo=user.passport_photo_id,
                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
                            parse_mode='Markdown',
                            disable_notification=False,
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            else:
                passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=passport_request.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
    
    elif query == 'curryear':
        direction = call_data[1]
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year, user_language, direction),
                                        )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass
    
    elif query == 'nextyear':
        direction = call_data[1]
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year + 1, user_language, direction),
                                        )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass

    elif query == 'parcel':
        await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
        await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

        parcel = Parcel(user=user)
        await sync_to_async(parcel.save)()
        
        user.curr_input = 'parcel_type'
        await sync_to_async(user.save)()

        choose = await sync_to_async(TGText.objects.get)(slug='choose_options', language=user_language)
        try:
            await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=choose.text,
                                    parse_mode='Markdown',
                                    )
            
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=await keyboards.parcel_types_keyboard(user_language),
                                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass
    
    elif query == 'parceltype':
        parcel_type_id = int(call_data[1])
        parcel_type = await sync_to_async(ParcelVariation.objects.filter(id=parcel_type_id).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if parcel and curr_input and curr_input == 'parcel_type':
            parcel.variation = parcel_type
            await sync_to_async(parcel.save)()
            user.curr_input = 'fio_receiver'
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            question = await sync_to_async(TGText.objects.get)(slug='fio_receiver_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
            
        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif query == 'confirm':
        info = call_data[1]

        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()

        if (flight and parcel) or (not flight and not parcel) or (not curr_input) or (curr_input != info):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        
        else:
            if info == 'name':
                user.curr_input = 'familyname'
                await sync_to_async(user.save)()

                if flight:
                    family_name = flight.family_name
                elif parcel:
                    family_name = parcel.family_name
                
                if family_name:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='familyname_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{family_name}*?'

                    try:
                        await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )
                    
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('familyname', user_language),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                    question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif info == 'familyname':
                user.curr_input = 'passportnum'
                await sync_to_async(user.save)()

                if flight:
                    passport_num = flight.passport_number
                elif parcel:
                    passport_num = parcel.passport_number
                
                if passport_num:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='passport_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{passport_num}*?'

                    try:
                        await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )
                    
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('passportnum', user_language),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif info == 'passportnum':
                user.curr_input = 'sex'
                await sync_to_async(user.save)()

                if flight:
                    sex = flight.sex
                elif parcel:
                    sex = parcel.sex
                
                if sex:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='sex_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{sex}*?'

                    try:
                        await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )
                    
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('sex', user_language),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                    question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                reply_markup=await keyboards.sex_keyboard(user_language),
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif info == 'sex':
                user.curr_input = 'birthdate'
                await sync_to_async(user.save)()

                if flight:
                    birth_date = flight.birth_date
                elif parcel:
                    birth_date = parcel.birth_date
                
                if birth_date:
                    birth_date = birth_date.strftime('%d.%m.%Y')

                    confirm_text = await sync_to_async(TGText.objects.get)(slug='birth_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{birth_date}*?'

                    try:
                        await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )
                    
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('birthdate', user_language),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                    question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif info == 'birthdate':
                user.curr_input = 'startdate'
                await sync_to_async(user.save)()

                if flight:
                    start_date = flight.start_date
                elif parcel:
                    start_date = parcel.start_date
                
                if start_date:
                    start_date = start_date.strftime('%d.%m.%Y')

                    confirm_text = await sync_to_async(TGText.objects.get)(slug='start_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{start_date}*?'

                    try:
                        await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )
                    
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('startdate', user_language),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                    question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif info == 'startdate':
                user.curr_input = 'enddate'
                await sync_to_async(user.save)()

                if flight:
                    end_date = flight.end_date
                elif parcel:
                    end_date = parcel.end_date
                
                if end_date:
                    end_date = end_date.strftime('%d.%m.%Y')

                    confirm_text = await sync_to_async(TGText.objects.get)(slug='end_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{end_date}*?'

                    try:
                        await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )
                    
                        await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('enddate', user_language),
                                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass

                    question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif info == 'enddate':
                user.curr_input = 'phone'
                await sync_to_async(user.save)()

                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                phone_question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                            text=phone_question.text,
                            parse_mode='Markdown',
                            reply_markup=await keyboards.request_phone_keyboard(user_language),
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            
            elif info == 'confirmation':
                user.curr_input = None

                if flight:
                    flight.complete = True 
                    user.name = flight.name
                    user.family_name = flight.family_name
                    user.passport_number = flight.passport_number
                    user.sex = flight.sex
                    user.birth_date = flight.birth_date
                    user.start_date = flight.start_date
                    user.end_date = flight.end_date
                    user.passport_photo_user = await sync_to_async(lambda: flight.passport_photo_flight)()
                    user.passport_photo_id = flight.passport_photo_id
                    user.phone = flight.phone
                    user.addresses = flight.address
                    user.lat = flight.lat
                    user.lon = flight.lon
                    await sync_to_async(flight.save)()

                elif parcel:
                    parcel.complete = True 
                    user.name = parcel.name
                    user.family_name = parcel.family_name
                    user.passport_number = parcel.passport_number
                    user.sex = parcel.sex
                    user.birth_date = parcel.birth_date
                    user.start_date = parcel.start_date
                    user.end_date = parcel.end_date
                    user.passport_photo_user = await sync_to_async(lambda: parcel.passport_photo_parcel)()
                    user.passport_photo_id =  parcel.passport_photo_id
                    user.phone = parcel.phone
                    user.addresses = parcel.address
                    user.lat = parcel.lat
                    user.lon = parcel.lon
                    await sync_to_async(parcel.save)()

                await sync_to_async(user.save)()

                try:
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass
                
                reply_text = await sync_to_async(TGText.objects.get)(slug='contact_soon', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                            text=reply_text.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
                
                name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                reply_text = f'Заявка от пользователя:\n\n'

                if flight:
                    route = await sync_to_async(TGText.objects.get)(slug='route', language=user_language)
                    flight_type = await sync_to_async(TGText.objects.get)(slug='type_flight', language=user_language)
                    departure_date = await sync_to_async(TGText.objects.get)(slug='departure', language=user_language)
                    arrival_date = await sync_to_async(TGText.objects.get)(slug='arrival', language=user_language)

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='oneway_button', language=user_language)
                    else:
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='roundtrip_button', language=user_language)

                    flight_route_db = await sync_to_async(lambda: flight.route.route)()

                    reply_text += f'\n*{route.text}* {flight_route_db}'
                    reply_text += f'\n*{flight_type.text.lower()}* {flight_type_text}'
                    reply_text += f'\n*{departure_date.text}* {flight.departure_date.strftime("%d.%m.%Y")}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date.text}* {flight.arrival_date.strftime("%d.%m.%Y")}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name.text}* {flight.name}'
                    reply_text += f'\n*{family_name.text}* {flight.family_name}'
                    reply_text += f'\n*{passport.text}* {flight.passport_number}'
                    reply_text += f'\n*{sex.text}* {flight.sex}'
                    reply_text += f'\n*{birth_date.text}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {flight.phone}'
                    reply_text += f'\n*{address.text}* {flight.address}'

                elif parcel:
                    parcel_type = await sync_to_async(TGText.objects.get)(slug='type_parcel', language=user_language)
                    items_list = await sync_to_async(TGText.objects.get)(slug='contains', language=user_language)
                    fio_receiver = await sync_to_async(TGText.objects.get)(slug='fio_receiver', language=user_language)
                    phone_receiver = await sync_to_async(TGText.objects.get)(slug='receiver_phone', language=user_language)

                    photo_id = parcel.passport_photo_id

                    parcel_variation_name_db = await sync_to_async(lambda: parcel.variation.name)()

                    reply_text += f'\n*{parcel_type.text}* {parcel_variation_name_db}'
                    reply_text += f'\n*{items_list.text}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver.text}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver.text}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name.text}* {parcel.name}'
                    reply_text += f'\n*{family_name.text}* {parcel.family_name}'
                    reply_text += f'\n*{passport.text}* {parcel.passport_number}'
                    reply_text += f'\n*{sex.text}* {parcel.sex}'
                    reply_text += f'\n*{birth_date.text}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {parcel.phone}'
                    reply_text += f'\n*{address.text}* {parcel.address}'

                try:
                    if flight:
                        info_type = 'flight'
                        info_id = flight.pk
                    elif parcel:
                        info_type = 'parcel'
                        info_id = parcel.pk
                    
                    await bot.send_photo(
                               chat_id=config.MANAGER_ID,
                               caption=reply_text,
                               photo=photo_id,
                               reply_markup=await keyboards.confirm_application_keyboard(info_type, info_id),
                               parse_mode='Markdown',
                               disable_notification=False,
                               )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=config.MANAGER_ID,
                            description=f'Не удалось отправить сообщение пользователю {config.MANAGER_ID} (менеджер). {info_type}, {info_id}',
                        )
                    except:
                        pass

            elif info == 'passport':
                confirm_application = await sync_to_async(TGText.objects.get)(slug='confirm_application', language=user_language)
                name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                user.curr_input = 'confirmation'

                if flight:
                    flight.name = user.name
                    flight.family_name = user.family_name
                    flight.passport_number = user.passport_number
                    flight.sex = user.sex
                    flight.birth_date = user.birth_date
                    flight.start_date = user.start_date
                    flight.end_date = user.end_date
                    flight.passport_photo_flight = await sync_to_async(lambda: user.passport_photo_user)()
                    flight.passport_photo_id = user.passport_photo_id
                    flight.phone = user.phone
                    flight.address = user.addresses
                    await sync_to_async(flight.save)()

                    route = await sync_to_async(TGText.objects.get)(slug='route', language=user_language)
                    flight_type = await sync_to_async(TGText.objects.get)(slug='type_flight', language=user_language)
                    departure_date = await sync_to_async(TGText.objects.get)(slug='departure', language=user_language)
                    arrival_date = await sync_to_async(TGText.objects.get)(slug='arrival', language=user_language)

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='oneway_button', language=user_language)
                    else:
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='roundtrip_button', language=user_language)

                    reply_text = f'{confirm_application.text}\n'

                    flight_route_db = await sync_to_async(lambda: flight.route.route)()

                    reply_text += f'\n*{route.text}* {flight_route_db}'
                    reply_text += f'\n*{flight_type.text.lower()}* {flight_type_text}'
                    reply_text += f'\n*{departure_date.text}* {flight.departure_date.strftime("%d.%m.%Y")}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date.text}* {flight.arrival_date.strftime("%d.%m.%Y")}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name.text}* {flight.name}'
                    reply_text += f'\n*{family_name.text}* {flight.family_name}'
                    reply_text += f'\n*{passport.text}* {flight.passport_number}'
                    reply_text += f'\n*{sex.text}* {flight.sex}'
                    reply_text += f'\n*{birth_date.text}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {flight.phone}'
                    reply_text += f'\n*{address.text}* {flight.address}'

                elif parcel:
                    parcel.name = user.name
                    parcel.family_name = user.family_name
                    parcel.passport_number = user.passport_number
                    parcel.sex = user.sex
                    parcel.birth_date = user.birth_date
                    parcel.start_date = user.start_date
                    parcel.end_date = user.end_date
                    parcel.passport_photo_parcel = await sync_to_async(lambda: user.passport_photo_user)()
                    parcel.passport_photo_id = user.passport_photo_id
                    parcel.phone = user.phone
                    parcel.address = user.addresses
                    await sync_to_async(parcel.save)()

                    parcel_type = await sync_to_async(TGText.objects.get)(slug='type_parcel', language=user_language)
                    items_list = await sync_to_async(TGText.objects.get)(slug='contains', language=user_language)
                    fio_receiver = await sync_to_async(TGText.objects.get)(slug='fio_receiver', language=user_language)
                    phone_receiver = await sync_to_async(TGText.objects.get)(slug='receiver_phone', language=user_language)

                    photo_id = parcel.passport_photo_id

                    reply_text = f'{confirm_application.text}\n'

                    parcel_variation_name_db = await sync_to_async(lambda: parcel.variation.name)()

                    reply_text += f'\n*{parcel_type.text}* {parcel_variation_name_db}'
                    reply_text += f'\n*{items_list.text}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver.text}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver.text}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name.text}* {parcel.name}'
                    reply_text += f'\n*{family_name.text}* {parcel.family_name}'
                    reply_text += f'\n*{passport.text}* {parcel.passport_number}'
                    reply_text += f'\n*{sex.text}* {parcel.sex}'
                    reply_text += f'\n*{birth_date.text}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {parcel.phone}'
                    reply_text += f'\n*{address.text}* {parcel.address}'

                await sync_to_async(user.save)()

                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass
                
                try:
                    await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=photo_id,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('confirmation', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
        
    elif query == 'hand':
        info = call_data[1]

        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()

        if (flight and parcel) or (not flight and not parcel) or (not curr_input) or (curr_input != info):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        
        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            if info == 'name':
                question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif info == 'familyname':
                question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif info == 'passportnum':
                question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif info == 'sex':
                question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            reply_markup=await keyboards.sex_keyboard(user_language),
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif info == 'birthdate':
                question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif info == 'startdate':
                question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif info == 'enddate':
                question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            
            elif info == 'passport':
                passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=passport_request.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

    elif query == 'sex':
        sex = call_data[1]

        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()

        if (flight and parcel) or (not flight and not parcel) or (not curr_input) or (curr_input != 'sex'):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            user.curr_input = 'birthdate'
            await sync_to_async(user.save)()

            if flight:
                flight.sex = sex
                birth_date = flight.birth_date
                await sync_to_async(flight.save)()
            elif parcel:
                parcel.sex = sex
                birth_date = parcel.birth_date
                await sync_to_async(parcel.save)()
            
            if birth_date:
                birth_date = birth_date.strftime('%d.%m.%Y')

                confirm_text = await sync_to_async(TGText.objects.get)(slug='birth_correct_question', language=user_language)
                reply_text = f'{confirm_text.text} *{birth_date}*?'

                try:
                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('birthdate', user_language),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass
                
            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            
    elif query == 'cancel':
        user.curr_input = None
        await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
        await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)

        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass

        reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)

        try:
            await bot.send_message(chat_id=chat_id,
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
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

    elif query == 'price':
        info_type = call_data[1]
        info_id = int(call_data[2])

        user.curr_input = f'{info_type}price_{info_id}'
        await sync_to_async(user.save)()

        try:
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass
        
        try:
            await bot.send_message(chat_id=chat_id,
                                text='Введите стоимость в шекелях',
                                parse_mode='Markdown',
                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

    elif query == 'refuse':
        info_type = call_data[1]
        info_id = int(call_data[2])
        
        if info_type == 'flight':
            application = await sync_to_async(Flight.objects.filter(id=info_id).first)()
        else:
            application = await sync_to_async(Parcel.objects.filter(id=info_id).first)()

        if application:
            application.confirmed = False
            await sync_to_async(application.save)()

        user.curr_input = None
        await sync_to_async(user.save)()

        try:
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass
        
        try:
            await bot.send_message(chat_id=chat_id,
                                text='Заявка отклонена.',
                                parse_mode='Markdown',
                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass
    
    elif query == 'complete':
        if user_id == config.MANAGER_ID:
            info_type = call_data[1]
            info_id = int(call_data[2])
            info_price = float(call_data[3])

            if info_type == 'flight':
                application = await sync_to_async(Flight.objects.filter(id=info_id).first)()
            else:
                application = await sync_to_async(Parcel.objects.filter(id=info_id).first)()
            
            if application:
                application.confirmed = True
                application.price = info_price
    
                stop_id = await send_pickup_address(application, info_type)
                if stop_id:
                    application.circuit_id = stop_id
                    application.circuit_api = True
                else:
                    application.circuit_api = False

                await sync_to_async(application.save)()

                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass
                
                try:
                    await bot.send_message(chat_id=chat_id,
                                text=f'Заявка подтверждена. Стоимость *{info_price} ₪*.',
                                parse_mode='Markdown',
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

    elif query == 'sim':
        users_sim = await sync_to_async(user.sim_cards.first)()
        if users_sim:
            fare = await sync_to_async(lambda: users_sim.fare)()
            fare_description = await sync_to_async(TGText.objects.get)(slug='fare_description', language=user_language)
            fare_price = await sync_to_async(TGText.objects.get)(slug='fare_price', language=user_language)
            short_month = await sync_to_async(TGText.objects.get)(slug='short_month', language=user_language)
            if users_sim.debt >= 0:
                sim_debt = await sync_to_async(TGText.objects.get)(slug='sim_debt', language=user_language)
            else:
                sim_debt = await sync_to_async(TGText.objects.get)(slug='sim_balance', language=user_language)
            reply_text = f'''
                          *{fare_description.text}*\
                          \n{fare.description}\
                          \n\
                          \n{fare_price.text} {fare.price}₪/{short_month.text}\
                          \n\
                          \n*{sim_debt.text}: {abs(users_sim.debt)}₪*\
                          '''
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            if users_sim.circuit_id_collect is None:
                curr_keyboard = await keyboards.ready_pay_only_keyboard(user_language)
            else:
                curr_keyboard = InlineKeyboardBuilder().as_markup()

            try:
                await bot.send_message(chat_id=chat_id,
                                        text=reply_text,
                                        reply_markup=curr_keyboard,
                                        parse_mode='Markdown',
                                        )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            user.curr_input = 'user_passport'
            await sync_to_async(user.save)()

            if user.passport_photo_id and user.addresses and user.name and user.family_name:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                reuse = await sync_to_async(TGText.objects.get)(slug='reuse', language=user_language)
                address_text = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                name_text = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                familyname_text = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                reply_text = f'{reuse.text}\n\n'
                reply_text += f'\n*{name_text.text}* {user.name}'
                reply_text += f'\n*{familyname_text.text}* {user.family_name}'
                reply_text += f'\n*{address_text.text}* {user.addresses}'

                try:
                    await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=user.passport_photo_id,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('s-confirmation', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            
            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=passport_request.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

    elif query == 's-confirm':
        info = call_data[1]

        if curr_input and curr_input == 'user_passport':
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            if info == 's-confirmation':
                user.curr_input = 'sim-fare'
                await sync_to_async(user.save)()

                choose_fare = await sync_to_async(TGText.objects.get)(slug='choose_fare', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                                text=choose_fare.text,
                                reply_markup=await keyboards.sim_fares_keyboard(),
                                parse_mode='Markdown',
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            
            else:
                error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
                try:
                    await bot.send_message(chat_id=user_id,
                                    text=error.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        elif curr_input and curr_input == 'sim-confirmation':
            try:
                fare_id = int(call_data[2])
            except:
                fare_id = None
            fare = await sync_to_async(SimFare.objects.filter(id=fare_id).first)()
            if info == 'fare' and fare:
                user.curr_input = None
                await sync_to_async(user.save)()
                
                address_text = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                fare_description = await sync_to_async(TGText.objects.get)(slug='fare_description', language=user_language)
                fare_price = await sync_to_async(TGText.objects.get)(slug='fare_price', language=user_language)

                name_text = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                familyname_text = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                #TODO:
                reply_text = f'''
                            *Заявка от пользователя на симку:*\
                            \n\
                            \n*{name_text.text}* {user.name}\
                            \n*{familyname_text.text}* {user.family_name}\
                            \n*{address_text.text}* {user.addresses}\
                            \n\
                            \n*{fare_description.text}*\
                            \n{fare.description}\
                            \n*{fare_price.text}* {fare.price}₪\
                            \n\
                            \nДля подтверждения необходимо будет внести номер выдаваемой симки\
                            '''
                if user.username:
                    reply_text += f'\n\nПользователь: @{user.username}. Telegram id: {user.user_id} (для связи через админку).'
                else:
                    reply_text += f'\n\nПользователь без валидного никнейма. Telegram id: {user.user_id} (для связи через админку).'

                try:
                    await bot.send_photo(chat_id=config.SIM_MANAGER_ID,
                                    caption=reply_text,
                                    photo=user.passport_photo_id,
                                    reply_markup=await keyboards.sim_confirm_application_keyboard(user.pk, fare.pk),
                                    parse_mode='Markdown',
                                    disable_notification=False,
                                    ) 
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=config.SIM_MANAGER_ID,
                            description=f'Не удалось отправить сообщение пользователю {config.SIM_MANAGER_ID} (менеджеру по симкартам). Запрос на создание симки от {user_id}, тариф {fare.title}',
                        )
                    except:
                        pass

                try:
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                if user.username:
                    reply_text = await sync_to_async(TGText.objects.get)(slug='contact_soon', language=user_language)
                else:
                    reply_text = await sync_to_async(TGText.objects.get)(slug='sim_application_accepted', language=user_language)

                try:
                    await bot.send_message(chat_id=chat_id,
                            text=reply_text.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
                
            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                                    text=error.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        elif curr_input and curr_input == 's-name' and info == 'name':
            user.curr_input = 's-familyname'
            await sync_to_async(user.save)()
            if user.family_name:
                confirm_text = await sync_to_async(TGText.objects.get)(slug='familyname_correct_question', language=user_language)
                reply_text = f'{confirm_text.text} *{user.family_name}*?'

                try:
                    await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=reply_text,
                                            parse_mode='Markdown',
                                            )

                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('familyname', user_language),
                                                        )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                                    text=question.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        elif curr_input and curr_input == 's-familyname' and info == 'familyname':
            user.curr_input = 'sim-fare'
            await sync_to_async(user.save)()

            choose_fare = await sync_to_async(TGText.objects.get)(slug='choose_fare', language=user_language)
            try:
                await bot.edit_message_text(chat_id=chat_id,
                                            message_id=message_id,
                                            text=choose_fare.text,
                                            parse_mode='Markdown',
                                            )

                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.sim_fares_keyboard(),
                                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

        elif info == 'address':
            sim_card = await sync_to_async(user.sim_cards.first)()

            if sim_card and sim_card.circuit_id_collect is None: # and sim_card.debt >= config.SIM_DEBT_LIMIT
                reply = await sync_to_async(TGText.objects.get)(slug='collect_sim_money', language=user_language)

                try:
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                        message_id=message_id,
                                                        reply_markup=InlineKeyboardBuilder().as_markup(),
                                                        )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass
                
                try:
                    await bot.send_message(chat_id=chat_id,
                                        text=reply.text,
                                        parse_mode='Markdown',
                                        )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

                stop_id = await send_sim_money_collect_address(sim_card.sim_phone, user, sim_card.debt)

                sim_card.ready_to_pay = True
                if stop_id:
                    sim_card.circuit_id_collect = stop_id
                    sim_card.circuit_api_collect = True
                else:
                    sim_card.circuit_api_collect = False

                await sync_to_async(sim_card.save)()

            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
                try:
                    await bot.send_message(chat_id=user_id,
                                    text=error.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif query == 's-hand':
        info = call_data[1]

        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass

        if curr_input and curr_input == 'user_passport':
            if info == 's-confirmation':
                passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                try:
                    await bot.send_message(chat_id=user_id,
                            text=passport_request.text,
                            parse_mode='Markdown',
                            )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

        elif curr_input and curr_input == 's-name' and info == 'name':
            question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        elif curr_input and curr_input == 's-familyname' and info == 'familyname':
            question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        elif info == 'address':
            user.lat = None
            user.lon = None
            user.curr_input = 'sim_collect_money_address'
            await sync_to_async(user.save)()

            address_question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=address_question.text,
                                reply_markup= await keyboards.request_location_keyboard(user_language),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif query == 'fare':
        fare_id = int(call_data[1])
        fare = await sync_to_async(SimFare.objects.filter(id=fare_id).first)()

        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass

        if curr_input and curr_input == 'sim-fare' and user.addresses and user.passport_photo_id and fare and user.name and user.family_name:
            user.curr_input = 'sim-confirmation'
            await sync_to_async(user.save)()

            confirm_application = await sync_to_async(TGText.objects.get)(slug='confirm_application', language=user_language)
            address_text = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            fare_description = await sync_to_async(TGText.objects.get)(slug='fare_description', language=user_language)
            fare_price = await sync_to_async(TGText.objects.get)(slug='fare_price', language=user_language)

            short_month = await sync_to_async(TGText.objects.get)(slug='short_month', language=user_language)
            new_sim_tax = await sync_to_async(TGText.objects.get)(slug='new_sim_tax', language=user_language)

            name_text = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
            familyname_text = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)

            reply_text = f'''
                        *{confirm_application.text}*\
                        \n\
                        \n*{name_text.text}* {user.name}\
                        \n*{familyname_text.text}* {user.family_name}\
                        \n*{address_text.text}* {user.addresses}\
                        \n\
                        \n*{fare_description.text}*\
                        \n{fare.description}\
                        \n*{fare_price.text}* {fare.price}₪/{short_month.text} {new_sim_tax.text}\
                        '''

            try:
                await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=user.passport_photo_id,
                                reply_markup=await keyboards.sim_confirmation_keyboard(fare_id, user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else: 
            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
    
    elif query == 's-cancel':
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass

        if curr_input and curr_input == 'sim-confirmation':
            user.curr_input = None
            await sync_to_async(user.save)()

            reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)

            try:
                await bot.send_message(chat_id=chat_id,
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
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif query == 'back':
        destination = call_data[1]

        if destination == 'fares':
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            if curr_input and curr_input == 'sim-confirmation':
                user.curr_input = 'sim-fare'
                await sync_to_async(user.save)()

                choose_fare = await sync_to_async(TGText.objects.get)(slug='choose_fare', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                                text=choose_fare.text,
                                reply_markup=await keyboards.sim_fares_keyboard(),
                                parse_mode='Markdown',
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            else:
                error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
                try:
                    await bot.send_message(chat_id=user_id,
                                    text=error.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

    elif query == 's-refuse':
        user.curr_input = None
        await sync_to_async(user.save)()

        try:
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='1',
                    main_user=user_id,
                    description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                )
            except:
                pass
        
        try:
            await bot.send_message(chat_id=chat_id,
                                text='Заявка отклонена.',
                                parse_mode='Markdown',
                                )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass
    
    elif query == 'm-sim':
        if user_id == config.SIM_MANAGER_ID:
            sim_user_id = int(call_data[1])
            fare_id = int(call_data[2])

            user.curr_input = f'manager-sim_{sim_user_id}_{fare_id}'
            await sync_to_async(user.save)()

            try:
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=chat_id,
                                    text='Введите номер выдаваемой симки',
                                    parse_mode='Markdown',
                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
    
    elif query == 's-retype':
        if user_id == config.SIM_MANAGER_ID:
            sim_user_id = int(call_data[1])
            fare_id = int(call_data[2])

            user.lat = None
            user.lon = None
            user.curr_input = f'manager-sim_{sim_user_id}_{fare_id}'
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=chat_id,
                                    text='Введите номер выдаваемой симки (должен начинаться с 972)',
                                    parse_mode='Markdown',
                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
    
    elif query == 's-complete':

        if user_id == config.SIM_MANAGER_ID:
            sim_user_id = int(call_data[1])
            fare_id = int(call_data[2])

            data = user.curr_input.split('_')
            phone = data[1]

            if curr_input and 'manager-sim' in curr_input and len(data) == 2:
                try:
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass
                
                sim_user = await sync_to_async(TGUser.objects.filter(id=sim_user_id).first)()
                fare = await sync_to_async(SimFare.objects.filter(id=fare_id).first)()

                icount_client_id = await create_icount_client(sim_user, phone)

                if icount_client_id:
                    icount_api = True
                    stop_id = await send_sim_delivery_address(phone, sim_user, fare)
                else:
                    icount_client_id = None
                    icount_api = False
                    stop_id = False
                
                if stop_id:
                    circuit_api = True
                else:
                    stop_id = None
                    circuit_api = False

                user.curr_input = None
                await sync_to_async(user.save)()

                users_sim = UsersSim(
                    user=sim_user,
                    fare=fare,
                    sim_phone=phone,
                    next_payment=(datetime.datetime.utcnow() + datetime.timedelta(days=31)).date(),
                    debt=(50 + fare.price),
                    circuit_id=stop_id,
                    icount_id=icount_client_id,
                    circuit_api=circuit_api,
                    icount_api=icount_api,
                )
                await sync_to_async(users_sim.save)()

                if stop_id and icount_client_id:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='1',
                                main_user=user_id,
                                description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                            )
                        except:
                            pass
                    
                    try:
                        await bot.send_message(chat_id=chat_id,
                                    text=f'Заявка подтверждена. Номер симки *{phone}*.',
                                    parse_mode='Markdown',
                                    )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass
                else:
                    try:
                        await bot.send_message(chat_id=chat_id,
                                    text=f'Ошибка при отправке в circuit или icount, воспользуйтесь админ панелью.',
                                    parse_mode='Markdown',
                                    )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='1',
                            main_user=user_id,
                            description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                        )
                    except:
                        pass

                error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
                try:
                    await bot.send_message(chat_id=user_id,
                                    text=error.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

    elif query == 'later':
        sim_card = await sync_to_async(user.sim_cards.first)()

        if sim_card and not sim_card.ready_to_pay:
            period = call_data[1]
            if period == 'week':
                days = 7
                debt = sim_card.debt
            elif period == 'month':
                days = 31
                fare_price = await sync_to_async(lambda: sim_card.fare.price)()
                debt = sim_card.debt + fare_price

            sim_card.pay_date = (datetime.datetime.utcnow() + datetime.timedelta(days=days)).date()
            sim_card.notified = False
            await sync_to_async(sim_card.save)()

            pay_date_text = await sync_to_async(TGText.objects.get)(slug='pay_date', language=user_language)
            sim_debt = await sync_to_async(TGText.objects.get)(slug='sim_debt_future', language=user_language)
            human_pay_date = sim_card.pay_date.strftime('%d.%m.%Y')
            reply_text = f'''
                    *{sim_card.sim_phone}*\
                    \n{sim_debt.text}:\
                    \n*{debt} ₪*\
                    \n{pay_date_text.text} *{human_pay_date}*\
                    '''

            try:
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass


    elif query == 'readypay':
        if user.addresses:
            address_question = await sync_to_async(TGText.objects.get)(slug='address_correct_question', language=user_language)
            reply_text = f'{address_question.text}\n*{user.addresses}*'

            try:
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=InlineKeyboardBuilder().as_markup(),
                                                    )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=chat_id,
                                text=reply_text,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('address', user_language),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass


        else:
            user.curr_input = 'sim_collect_money_address'
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass

            address_question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=address_question.text,
                                reply_markup= await keyboards.request_location_keyboard(user_language),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass


@dp.message(ChatTypeFilter(chat_type='private'), F.photo)
async def handle_photo(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    photo = message.photo[-1].file_id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')
    curr_input = user.curr_input

    if curr_input and curr_input == 'passport':
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if (flight and parcel) or (not flight and not parcel):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            counter = 0
            try:
                file_info = await bot.get_file(photo)
                downloaded_file = await bot.download_file(file_info.file_path)
                
                photo_info = await functions.parse_passport(downloaded_file)
            except Exception as ex:
                counter = config.PARSE_COUNT
                photo_info = [None, None, None, None, None, None, None]

                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='7',
                        main_user=user_id,
                        description=f'Не удалось обработать фото пользователя {user_id}. {ex}',
                    )
                except:
                    pass


            for info in photo_info:
                if info:
                    counter += 1

            if counter >= config.PARSE_COUNT:
                folder, _ = await sync_to_async(Folder.objects.get_or_create)(name="Паспорта")

                if flight:
                    slug = 'flight'
                    pk = flight.pk
                elif parcel:
                    slug = 'parcel'
                    pk = parcel.pk

                try:
                    passport = Image(
                        folder=folder,
                        original_filename=f"{slug}_{pk}.{file_info.file_path.split('.')[-1]}",
                    )
                    await sync_to_async(passport.file.save)(passport.original_filename, downloaded_file)
                    await sync_to_async(passport.save)()
                except Exception as ex:
                    passport = None
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='7',
                            main_user=user_id,
                            description=f'Не удалось сохранить фото пользователя {user_id}. {ex}',
                        )
                    except:
                        pass


                name, family_name, passport_number, sex, birth_date, start_date, end_date = photo_info

                if flight:
                    flight.passport_photo_flight = passport
                    flight.name = await utils.escape_markdown(name)
                    flight.family_name = await utils.escape_markdown(family_name)
                    flight.passport_number = passport_number
                    flight.sex = sex
                    flight.birth_date = birth_date
                    flight.start_date = start_date
                    flight.end_date = end_date
                    flight.passport_photo_id = photo
                    await sync_to_async(flight.save)()

                elif parcel:
                    parcel.passport_photo_parcel = passport
                    parcel.name = await utils.escape_markdown(name)
                    parcel.family_name = await utils.escape_markdown(family_name)
                    parcel.passport_number = passport_number
                    parcel.sex = sex
                    parcel.birth_date = birth_date
                    parcel.start_date = start_date
                    parcel.end_date = end_date
                    parcel.passport_photo_id = photo
                    await sync_to_async(parcel.save)()
                
                user.curr_input = 'name'
                await sync_to_async(user.save)()

                if name:
                    name_confirm = await sync_to_async(TGText.objects.get)(slug='name_correct_question', language=user_language)
                    reply_text = f'{name_confirm.text} *{name}*?'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('name', user_language),
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

                else:
                    name_question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=name_question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            else:
                wrong_passport = await sync_to_async(TGText.objects.get)(slug='wrong_passport', language=user_language)
                try:
                    await bot.send_message(chat_id=user_id,
                                    text=wrong_passport.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

    elif curr_input and curr_input == 'user_passport':
        counter = 0
        try:
            file_info = await bot.get_file(photo)
            downloaded_file = await bot.download_file(file_info.file_path)
            
            photo_info = await functions.parse_passport(downloaded_file)
        except Exception as ex:
            counter = config.PARSE_COUNT
            photo_info = [None, None, None, None, None, None, None]

            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='7',
                    main_user=user_id,
                    description=f'Не удалось обработать фото пользователя {user_id}. {ex}',
                )
            except:
                pass


        for info in photo_info:
            if info:
                counter += 1

        if counter >= config.PARSE_COUNT:
            folder, _ = await sync_to_async(Folder.objects.get_or_create)(name="Паспорта")

            try:
                passport = Image(
                    folder=folder,
                    original_filename=f"{uuid.uuid4()}_{user.pk}.{file_info.file_path.split('.')[-1]}",
                )
                await sync_to_async(passport.file.save)(passport.original_filename, downloaded_file)
                await sync_to_async(passport.save)()
            except Exception as ex:
                passport = None
                
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='7',
                        main_user=user_id,
                        description=f'Не удалось сохранить фото пользователя {user_id}. {ex}',
                    )
                except:
                    pass

            name, family_name, passport_number, sex, birth_date, start_date, end_date = photo_info

            user.passport_photo_user = passport
            if name:
                user.name = await utils.escape_markdown(name)
            if family_name:
                user.family_name = await utils.escape_markdown(family_name)
            if passport_number:
                user.passport_number = passport_number
            if sex:
                user.sex = sex
            if birth_date:
                user.birth_date = birth_date
            if start_date:
                user.start_date = start_date
            if end_date:
                user.end_date = end_date
            user.passport_photo_id = photo
            user.curr_input = 's-address'
            await sync_to_async(user.save)()

            question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=question.text,
                                reply_markup=await keyboards.request_location_keyboard(user_language),
                                parse_mode='Markdown',
                                disable_notification=True,
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            wrong_passport = await sync_to_async(TGText.objects.get)(slug='wrong_passport', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=wrong_passport.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass


@dp.message(ChatTypeFilter(chat_type='private'), F.contact)
async def handle_contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = str(message.from_user.id)
    username = message.from_user.username
    chat_id = message.chat.id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')
    curr_input = user.curr_input

    if curr_input and curr_input == 'phone':
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if (flight and parcel) or (not flight and not parcel):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error,
                                reply_markup=types.ReplyKeyboardRemove(),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        else:
            user.curr_input = 'address'
            await sync_to_async(user.save)()

            if flight:
                flight.phone = phone
                await sync_to_async(flight.save)()
            elif parcel:
                parcel.phone = phone
                await sync_to_async(parcel.save)()

            question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                reply_markup=await keyboards.request_location_keyboard(user_language),
                                parse_mode='Markdown',
                                disable_notification=True,
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass


@dp.message(ChatTypeFilter(chat_type='private'), F.text)
async def handle_text(message):
    """Handles message with type text."""

    user_id = str(message.from_user.id)
    username = message.from_user.username
    chat_id = message.chat.id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')

    curr_input = user.curr_input
    input_info = await utils.escape_markdown(message.text)

    if curr_input and 'flightprice' in curr_input and user_id == config.MANAGER_ID:
        data = curr_input.split('_')
        flight_id = int(data[1])
        price = round(await utils.validate_price(input_info), 2)

        if price:
            try:
                await bot.send_message(chat_id=user_id,
                                text=f'Стоимость *{price} ₪*?',
                                reply_markup=await keyboards.confirm_price_keyboard('flight', flight_id, price),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            try:
                await bot.send_message(chat_id=user_id,
                                text='Не похоже на корректную стоимость, введите еще раз стоимость в шекелях.',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif curr_input and 'parcelprice' in curr_input and user_id == config.MANAGER_ID:
        data = curr_input.split('_')
        parcel_id = int(data[1])
        price = await utils.validate_price(input_info)

        if price:
            try:
                await bot.send_message(chat_id=user_id,
                                text=f'Стоимость *{price} ₪*?',
                                reply_markup=await keyboards.confirm_price_keyboard('parcel', parcel_id, price),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            try:
                await bot.send_message(chat_id=user_id,
                                text='Не похоже на корректную стоимость, введите еще раз стоимость в шекелях.',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif curr_input and 'manager-sim' in curr_input and user_id == config.SIM_MANAGER_ID:
        data = curr_input.split('_')
        sim_user_id = int(data[1])
        fare_id = int(data[2])
        phone = await utils.validate_phone_sim(input_info)
        if phone:
            user.curr_input = f'manager-sim_{phone}'
            await sync_to_async(user.save)()

            try:
                await bot.send_message(chat_id=user_id,
                                text=f'Номер телефона выдаваемой симки: *{phone}*?',
                                reply_markup=await keyboards.sim_confirm_phone_keyboard(sim_user_id, fare_id),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        else:
            try:
                await bot.send_message(chat_id=user_id,
                                text='Не похоже на корректный номер телефона, введите еще раз (должен начинаться с 972).',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif curr_input and curr_input == 's-address':
        user.addresses = input_info 
        user.curr_input = 's-name'
        await sync_to_async(user.save)()

        if user.name:
            confirm_text = await sync_to_async(TGText.objects.get)(slug='name_correct_question', language=user_language)
            reply_text = f'{confirm_text.text} *{user.name}*?'

            try:
                question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                await bot.send_message(chat_id=user_id,
                                text=f'{question.text} *{input_info}*',
                                reply_markup=types.ReplyKeyboardRemove(),
                                parse_mode='Markdown',
                                disable_notification=True,
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
            
            try:
                await bot.send_message(chat_id=chat_id,
                                text=reply_text,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('name', user_language),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                reply_markup=types.ReplyKeyboardRemove(),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
    
    elif curr_input and curr_input == 's-name':
        user.name = input_info 
        user.curr_input = 's-familyname'
        await sync_to_async(user.save)()

        if user.family_name:
            confirm_text = await sync_to_async(TGText.objects.get)(slug='familyname_correct_question', language=user_language)
            reply_text = f'{confirm_text.text} *{user.family_name}*?'

            try:
                await bot.send_message(chat_id=chat_id,
                                text=reply_text,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('familyname', user_language),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass
        else:
            question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
            except:
                pass

    elif curr_input and curr_input == 's-familyname':
        user.family_name = input_info 
        user.curr_input = 'sim-fare'
        await sync_to_async(user.save)()

        choose_fare = await sync_to_async(TGText.objects.get)(slug='choose_fare', language=user_language)
        try:
            await bot.send_message(chat_id=chat_id,
                            text=choose_fare.text,
                            reply_markup=await keyboards.sim_fares_keyboard(),
                            parse_mode='Markdown',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

    elif curr_input and curr_input == 'sim_collect_money_address':
        user.curr_input = None
        user.addresses = input_info
        await sync_to_async(user.save)()

        address_question = await sync_to_async(TGText.objects.get)(slug='address_correct_question', language=user_language)
        reply_text = f'{address_question.text}\n*{input_info}*'

        try:
            question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=f'{question.text} *{input_info}*',
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            disable_notification=True,
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass
        
        try:
            await bot.send_message(chat_id=chat_id,
                                    text=reply_text,
                                    reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('address', user_language),
                                    parse_mode='Markdown',
                                    )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

    elif curr_input:
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if (flight and parcel) or (not flight and not parcel):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                reply_markup=types.ReplyKeyboardRemove(),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            if curr_input == 'name':
                if flight:
                    flight.name = input_info
                    family_name = flight.family_name
                    await sync_to_async(flight.save)()
                elif parcel:
                    parcel.name = input_info
                    family_name = parcel.family_name
                    await sync_to_async(parcel.save)()
                
                user.curr_input = 'familyname'
                await sync_to_async(user.save)()

                if family_name:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='familyname_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{family_name}*?'

                    try:
                        await bot.send_message(chat_id=chat_id,
                                        text=reply_text,
                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('familyname', user_language),
                                        parse_mode='Markdown',
                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

                else:
                    question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'familyname':
                if flight:
                    flight.family_name = input_info
                    passport_num = flight.passport_number
                    await sync_to_async(flight.save)()
                elif parcel:
                    parcel.family_name = input_info
                    passport_num = parcel.passport_number
                    await sync_to_async(parcel.save)()
                
                user.curr_input = 'passportnum'
                await sync_to_async(user.save)()

                if passport_num:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='passport_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{passport_num}*?'

                    try:
                        await bot.send_message(chat_id=chat_id,
                                        text=reply_text,
                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('passportnum', user_language),
                                        parse_mode='Markdown',
                                        )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

                else:
                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'passportnum':
                passport_num = await utils.validate_passport(input_info)
                if passport_num:
                    if flight:
                        flight.passport_number = passport_num
                        await sync_to_async(flight.save)()
                        sex = flight.sex
                    elif parcel:
                        parcel.passport_number = passport_num
                        await sync_to_async(parcel.save)()
                        sex = parcel.sex
                    
                    user.curr_input = 'sex'
                    await sync_to_async(user.save)()

                    if sex:
                        confirm_text = await sync_to_async(TGText.objects.get)(slug='sex_correct_question', language=user_language)
                        reply_text = f'{confirm_text.text} *{sex}*?'

                        try:
                            await bot.send_message(chat_id=chat_id,
                                                text=reply_text,
                                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('sex', user_language),
                                                parse_mode='Markdown',
                                                )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                    else:
                        question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                        try:
                            await bot.send_message(chat_id=user_id,
                                    text=question.text,
                                    reply_markup=await keyboards.sex_keyboard(user_language),
                                    parse_mode='Markdown',
                                    )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'birthdate':
                birth_date = await utils.validate_date(input_info)
                if birth_date:
                    if flight:
                        flight.birth_date = birth_date
                        await sync_to_async(flight.save)()
                        start_date = flight.start_date
                    elif parcel:
                        parcel.birth_date = birth_date
                        await sync_to_async(parcel.save)()
                        start_date = parcel.start_date
                    
                    user.curr_input = 'startdate'
                    await sync_to_async(user.save)()

                    if start_date:
                        start_date = start_date.strftime('%d.%m.%Y')

                        confirm_text = await sync_to_async(TGText.objects.get)(slug='start_correct_question', language=user_language)
                        reply_text = f'{confirm_text.text} *{start_date}*?'

                        try:
                            await bot.send_message(chat_id=chat_id,
                                                text=reply_text,
                                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('startdate', user_language),
                                                parse_mode='Markdown',
                                                )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                    else:
                        question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

                        try:
                            await bot.send_message(chat_id=user_id,
                                    text=question.text,
                                    parse_mode='Markdown',
                                    )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'startdate':
                start_date = await utils.validate_date(input_info)
                if start_date:
                    if flight:
                        flight.start_date = start_date
                        await sync_to_async(flight.save)()
                        end_date = flight.end_date
                    elif parcel:
                        parcel.start_date = start_date
                        await sync_to_async(parcel.save)()
                        end_date = parcel.end_date
                    
                    user.curr_input = 'enddate'
                    await sync_to_async(user.save)()

                    if end_date:
                        end_date = end_date.strftime('%d.%m.%Y')

                        confirm_text = await sync_to_async(TGText.objects.get)(slug='end_correct_question', language=user_language)
                        reply_text = f'{confirm_text.text} *{end_date}*?'

                        try:
                            await bot.send_message(chat_id=chat_id,
                                                text=reply_text,
                                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('enddate', user_language),
                                                parse_mode='Markdown',
                                                )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                    else:
                        question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)

                        try:
                            await bot.send_message(chat_id=user_id,
                                    text=question.text,
                                    parse_mode='Markdown',
                                    )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass
                
                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'enddate':
                end_date = await utils.validate_date(input_info)
                if end_date:
                    if flight:
                        flight.end_date = end_date
                        await sync_to_async(flight.save)()
                    elif parcel:
                        parcel.end_date = end_date
                        await sync_to_async(parcel.save)()
                    
                    user.curr_input = 'phone'
                    await sync_to_async(user.save)()

                    phone_question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)

                    try:
                        await bot.send_message(chat_id=chat_id,
                                text=phone_question.text,
                                parse_mode='Markdown',
                                reply_markup=await keyboards.request_phone_keyboard(user_language),
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'phone':
                phone = await utils.validate_phone(input_info)
                if phone:
                    if flight:
                        flight.phone = phone
                        await sync_to_async(flight.save)()
                    elif parcel:
                        parcel.phone = phone
                        await sync_to_async(parcel.save)()

                    user.curr_input = 'address'
                    await sync_to_async(user.save)()

                    question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
                    try:
                        await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                reply_markup=await keyboards.request_location_keyboard(user_language),
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass
                
                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass

            elif curr_input == 'address':
                try:
                    question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                    await bot.send_message(chat_id=user_id,
                                    text=f'{question.text} *{input_info}*',
                                    reply_markup=types.ReplyKeyboardRemove(),
                                    parse_mode='Markdown',
                                    disable_notification=True,
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
                
                confirm_application = await sync_to_async(TGText.objects.get)(slug='confirm_application', language=user_language)
                name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                if flight:
                    flight.address = input_info
                    await sync_to_async(flight.save)()

                    route = await sync_to_async(TGText.objects.get)(slug='route', language=user_language)
                    flight_type = await sync_to_async(TGText.objects.get)(slug='type_flight', language=user_language)
                    departure_date = await sync_to_async(TGText.objects.get)(slug='departure', language=user_language)
                    arrival_date = await sync_to_async(TGText.objects.get)(slug='arrival', language=user_language)

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='oneway_button', language=user_language)
                    else:
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='roundtrip_button', language=user_language)

                    reply_text = f'{confirm_application.text}\n'

                    flight_route_db = await sync_to_async(lambda: flight.route.route)()

                    reply_text += f'\n*{route.text}* {flight_route_db}'
                    reply_text += f'\n*{flight_type.text.lower()}* {flight_type_text}'
                    reply_text += f'\n*{departure_date.text}* {flight.departure_date.strftime("%d.%m.%Y")}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date.text}* {flight.arrival_date.strftime("%d.%m.%Y")}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name.text}* {flight.name}'
                    reply_text += f'\n*{family_name.text}* {flight.family_name}'
                    reply_text += f'\n*{passport.text}* {flight.passport_number}'
                    reply_text += f'\n*{sex.text}* {flight.sex}'
                    reply_text += f'\n*{birth_date.text}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {flight.phone}'
                    reply_text += f'\n*{address.text}* {flight.address}'

                elif parcel:
                    parcel.address = input_info
                    await sync_to_async(parcel.save)()

                    parcel_type = await sync_to_async(TGText.objects.get)(slug='type_parcel', language=user_language)
                    items_list = await sync_to_async(TGText.objects.get)(slug='contains', language=user_language)
                    fio_receiver = await sync_to_async(TGText.objects.get)(slug='fio_receiver', language=user_language)
                    phone_receiver = await sync_to_async(TGText.objects.get)(slug='receiver_phone', language=user_language)

                    photo_id = parcel.passport_photo_id

                    reply_text = f'{confirm_application.text}\n'

                    parcel_variation_name_db = await sync_to_async(lambda: parcel.variation.name)()

                    reply_text += f'\n*{parcel_type.text}* {parcel_variation_name_db}'
                    reply_text += f'\n*{items_list.text}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver.text}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver.text}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name.text}* {parcel.name}'
                    reply_text += f'\n*{family_name.text}* {parcel.family_name}'
                    reply_text += f'\n*{passport.text}* {parcel.passport_number}'
                    reply_text += f'\n*{sex.text}* {parcel.sex}'
                    reply_text += f'\n*{birth_date.text}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {parcel.phone}'
                    reply_text += f'\n*{address.text}* {parcel.address}'

                user.curr_input = 'confirmation'
                await sync_to_async(user.save)()

                try:
                    await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=photo_id,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('confirmation', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
        
            elif parcel and curr_input == 'fio_receiver':
                parcel.fio_receiver = input_info
                await sync_to_async(parcel.save)()

                user.curr_input = 'contains'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='contains_question', language=user_language)
                try:
                    await bot.send_message(chat_id=chat_id,
                                    text=question.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass
            
            elif parcel and curr_input == 'contains':
                parcel.items_list = input_info
                await sync_to_async(parcel.save)()

                user.curr_input = 'phone_receiver'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='phone_receiver_question', language=user_language)

                try:
                    await bot.send_message(chat_id=chat_id,
                                    text=question.text,
                                    parse_mode='Markdown',
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

            elif parcel and curr_input == 'phone_receiver':
                phone_receiver = await utils.validate_phone(input_info)
                if phone_receiver:
                    parcel.phone_receiver = phone_receiver
                    await sync_to_async(parcel.save)()

                    user.curr_input = 'passport'
                    await sync_to_async(user.save)()

                    if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
                    user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                        reuse = await sync_to_async(TGText.objects.get)(slug='reuse', language=user_language)
                        name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                        family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                        passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                        sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                        birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                        start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                        end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                        phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                        address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                        reply_text = f'{reuse.text}\n'
                        
                        reply_text += f'\n*{name.text}* {user.name}'
                        reply_text += f'\n*{family_name.text}* {user.family_name}'
                        reply_text += f'\n*{passport.text}* {user.passport_number}'
                        reply_text += f'\n*{sex.text}* {user.sex}'
                        reply_text += f'\n*{birth_date.text}* {user.birth_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{start_date.text}* {user.start_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{end_date.text}* {user.end_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{phone.text}* {user.phone}'
                        reply_text += f'\n*{address.text}* {user.addresses}'

                        try:
                            await bot.send_photo(chat_id=user_id,
                                    caption=reply_text,
                                    photo=user.passport_photo_id,
                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
                                    parse_mode='Markdown',
                                    disable_notification=False,
                                    )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                    else:
                        passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                        try:
                            await bot.send_message(chat_id=user_id,
                                    text=passport_request.text,
                                    parse_mode='Markdown',
                                    )
                        except:
                            try:
                                await sync_to_async(AppError.objects.create)(
                                    source='1',
                                    error_type='2',
                                    main_user=user_id,
                                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                                )
                            except:
                                pass

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='phone_receiver_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await bot.send_message(chat_id=user_id,
                                text=reply_text,
                                parse_mode='Markdown',
                                )
                    except:
                        try:
                            await sync_to_async(AppError.objects.create)(
                                source='1',
                                error_type='2',
                                main_user=user_id,
                                description=f'Не удалось отправить сообщение пользователю {user_id}.',
                            )
                        except:
                            pass
    
    else:
        await sync_to_async(UserMessage.objects.create)(
            user=user,
            message=input_info,
        )


@dp.message(ChatTypeFilter(chat_type='private'), F.location)
async def handle_location(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    chat_id = message.chat.id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')

    curr_input = user.curr_input

    if curr_input and curr_input == 's-address':
        lat = message.location.latitude
        lon = message.location.longitude
        try:
            address = await get_address(lat, lon)
        except:
            address = 'Israel'

        try:
            question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=f'{question.text} *{address}*',
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            disable_notification=True,
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

        user.lat = lat
        user.lon = lon
        user.addresses = address
        user.curr_input = 's-name'
        await sync_to_async(user.save)()

        if user.name:
            confirm_text = await sync_to_async(TGText.objects.get)(slug='name_correct_question', language=user_language)
            reply_text = f'{confirm_text.text} *{user.name}*?'

            try:
                await bot.send_message(chat_id=chat_id,
                                text=reply_text,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('name', user_language),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)
            try:
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

    elif curr_input and curr_input == 'sim_collect_money_address':
        lat = message.location.latitude
        lon = message.location.longitude
        try:
            address = await get_address(lat, lon)
        except:
            address = 'Israel'

        try:
            question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=f'{question.text} *{address}*',
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            disable_notification=True,
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass

        user.lat = lat
        user.lon = lon
        user.addresses = address
        user.curr_input = None
        await sync_to_async(user.save)()

        address_question = await sync_to_async(TGText.objects.get)(slug='address_correct_question', language=user_language)
        reply_text = f'{address_question.text}\n*{address}*'

        try:
            await bot.send_message(chat_id=chat_id,
                                    text=reply_text,
                                    reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('address', user_language),
                                    parse_mode='Markdown',
                                    )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass
    
    elif curr_input:
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if (flight and parcel) or (not flight and not parcel):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)

            try:
                await bot.send_message(chat_id=user_id,
                                text=error.text,
                                reply_markup=types.ReplyKeyboardRemove(),
                                parse_mode='Markdown',
                                )
            except:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='2',
                        main_user=user_id,
                        description=f'Не удалось отправить сообщение пользователю {user_id}.',
                    )
                except:
                    pass

        else:
            if curr_input == 'address':
                confirm_application = await sync_to_async(TGText.objects.get)(slug='confirm_application', language=user_language)
                name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                lat = message.location.latitude
                lon = message.location.longitude
                try:
                    location_address = await get_address(lat, lon)
                except:
                    location_address = 'Israel'

                try:
                    question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                    await bot.send_message(chat_id=user_id,
                                    text=f'{question.text} *{location_address}*',
                                    reply_markup=types.ReplyKeyboardRemove(),
                                    parse_mode='Markdown',
                                    disable_notification=True,
                                    )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass

                if flight:
                    flight.address = location_address
                    await sync_to_async(flight.save)()

                    route = await sync_to_async(TGText.objects.get)(slug='route', language=user_language)
                    flight_type = await sync_to_async(TGText.objects.get)(slug='type_flight', language=user_language)
                    departure_date = await sync_to_async(TGText.objects.get)(slug='departure', language=user_language)
                    arrival_date = await sync_to_async(TGText.objects.get)(slug='arrival', language=user_language)

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='oneway_button', language=user_language)
                    else:
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='roundtrip_button', language=user_language)

                    reply_text = f'{confirm_application.text}\n'

                    flight_route_db = await sync_to_async(lambda: flight.route.route)()

                    reply_text += f'\n*{route.text}* {flight_route_db}'
                    reply_text += f'\n*{flight_type.text.lower()}* {flight_type_text}'
                    reply_text += f'\n*{departure_date.text}* {flight.departure_date.strftime("%d.%m.%Y")}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date.text}* {flight.arrival_date.strftime("%d.%m.%Y")}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name.text}* {flight.name}'
                    reply_text += f'\n*{family_name.text}* {flight.family_name}'
                    reply_text += f'\n*{passport.text}* {flight.passport_number}'
                    reply_text += f'\n*{sex.text}* {flight.sex}'
                    reply_text += f'\n*{birth_date.text}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {flight.phone}'
                    reply_text += f'\n*{address.text}* {flight.address}'

                elif parcel:
                    parcel.address = location_address
                    await sync_to_async(parcel.save)()

                    parcel_type = await sync_to_async(TGText.objects.get)(slug='type_parcel', language=user_language)
                    items_list = await sync_to_async(TGText.objects.get)(slug='contains', language=user_language)
                    fio_receiver = await sync_to_async(TGText.objects.get)(slug='fio_receiver', language=user_language)
                    phone_receiver = await sync_to_async(TGText.objects.get)(slug='receiver_phone', language=user_language)

                    photo_id = parcel.passport_photo_id

                    reply_text = f'{confirm_application.text}\n'

                    parcel_variation_name_db = await sync_to_async(lambda: parcel.variation.name)()

                    reply_text += f'\n*{parcel_type.text}* {parcel_variation_name_db}'
                    reply_text += f'\n*{items_list.text}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver.text}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver.text}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name.text}* {parcel.name}'
                    reply_text += f'\n*{family_name.text}* {parcel.family_name}'
                    reply_text += f'\n*{passport.text}* {parcel.passport_number}'
                    reply_text += f'\n*{sex.text}* {parcel.sex}'
                    reply_text += f'\n*{birth_date.text}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {parcel.phone}'
                    reply_text += f'\n*{address.text}* {parcel.address}'

                user.curr_input = 'confirmation'
                await sync_to_async(user.save)()

                try:
                    await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=photo_id,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('confirmation', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )
                except:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}.',
                        )
                    except:
                        pass


@dp.message(ChatTypeFilter(chat_type='group'), F.text)
async def handle_text(message):
    reply_text = message.text
    if message.reply_to_message:
        text = message.reply_to_message.text

        if 'TG id: ' in text:
            tg_id = await utils.extract_tg_id(text)

            if tg_id:
                user = await sync_to_async(TGUser.objects.filter(user_id=tg_id).first)()
                if user:
                    await sync_to_async(Notification.objects.create)(
                                user=user,
                                text=reply_text,
                            )


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
