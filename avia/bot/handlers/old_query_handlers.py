import os
import datetime

import django

from aiogram import Router
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from django.db.models import Q

from money_transfer.models import Rate
from core.models import (TGUser, TGText, Language, Parcel, Flight, Route, Day, ParcelVariation, SimFare, 
                         UsersSim, Question)
from errors.models import AppError
from core.utils import (send_pickup_address, send_sim_delivery_address, send_sim_money_collect_address,
                        create_icount_client,)

import config
import keyboards
from bot.new_keyboards import new_keyboards


router = Router()


@router.callback_query()
async def callback_query(call: types.CallbackQuery, state: FSMContext):
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
                await call.message.edit_text(
                                        text=choose_flight_type.text,
                                        parse_mode='Markdown',
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
                await call.message.delete()
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
                await call.message.answer(
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
                await call.message.edit_text(
                                        text=departure_text.text,
                                        parse_mode='Markdown',
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
                await call.message.delete()
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
                await call.message.answer(
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
                    await call.message.edit_text(
                                        text=departure_day.text,
                                        parse_mode='Markdown',
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
                    await call.answer(
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
                    await call.message.edit_text(
                                        text=arrival_day.text,
                                        parse_mode='Markdown',
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
                    await call.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
                    await call.message.edit_text(
                                            text=arrival_text.text,
                                            parse_mode='Markdown',
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
                    await call.message.delete()
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
                        await call.message.answer_photo(
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
                        await call.message.answer(
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
                await call.message.delete()
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
                    await call.message.answer_photo(
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
                    await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
            await call.message.edit_reply_markup(
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
            await call.message.edit_reply_markup(
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
            await call.message.edit_text(
                                    text=choose.text,
                                    parse_mode='Markdown',
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
                await call.message.delete()
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
                await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
                        await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                        await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                        await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                        await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                        await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                        await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                    await call.message.delete()
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
                    await call.message.answer(
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
                    await call.message.edit_reply_markup(
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
                    await call.message.answer(
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
                    
                    await call.bot.send_photo(
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
                    await call.message.delete()
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
                    await call.message.answer_photo(chat_id=user_id,
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
                await call.message.delete()
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
                await call.message.answer(
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
                await call.message.delete()
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                    await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
                    await call.message.edit_text(
                                        text=reply_text,
                                        parse_mode='Markdown',
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
                    await call.message.delete()
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
                    await call.message.answer(
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
            await call.message.delete()
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
            await call.message.answer(
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
            await call.message.edit_reply_markup(
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
            await call.message.answer(
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
            await call.message.edit_reply_markup(
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
            await call.message.answer(
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
                    await call.message.delete()
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
                    await call.message.answer(
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
                          *{fare_description.text} ({users_sim.sim_phone})* \
                          \n{fare.description}\
                          \n\
                          \n{fare_price.text} {fare.price}₪/{short_month.text}\
                          \n\
                          \n*{sim_debt.text}: {abs(users_sim.debt)}₪*\
                          '''
            try:
                await call.message.delete()
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
                reply_text += '\n\nЕсли готовы оплатить *сегодня*, нажмите на кнопку *Готов оплатить* ниже!'
            else:
                curr_keyboard = InlineKeyboardBuilder().as_markup()

            try:
                await call.message.answer(
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

            if user.addresses and user.name and user.family_name:
                reuse = await sync_to_async(TGText.objects.get)(slug='reuse', language=user_language)
                address_text = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                name_text = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                familyname_text = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                reply_text = f'{reuse.text}\n'
                reply_text += f'\n*{name_text.text}* {user.name}'
                reply_text += f'\n*{familyname_text.text}* {user.family_name}'
                reply_text += f'\n*{address_text.text}* {user.addresses}'

                try:
                    await call.message.edit_text(
                                text=reply_text,
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
                    await call.message.delete()
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

                user.curr_input = 's-address'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
                try:   
                    await call.message.answer(
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

    elif query == 's-confirm':
        info = call_data[1]

        if curr_input and curr_input == 'user_passport':
            if info == 's-confirmation':
                user.curr_input = 's-phone'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='sim_phone_question', language=user_language)
                try:
                    await call.message.edit_text(
                                    text=question.text,
                                    reply_markup=await new_keyboards.skip_sim_phone_keyboard(user_language),
                                    parse_mode='Markdown',
                                    )
                except Exception as e:
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='2',
                            main_user=user_id,
                            description=f'Не удалось отправить сообщение пользователю {user_id}. {e}',
                        )
                    except:
                        pass
            
            else:
                error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
                try:
                    await call.message.edit_text(
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
                data = await state.get_data()
                if user_entered_phone := data.get('phone'):
                    reply_text += f'\nНомер телефона указанный пользователем: *{user_entered_phone}*.'

                if user.username:
                    reply_text += f'\n\nПользователь: *@{user.username}*. Telegram id: {user.user_id} (для связи через админку).'
                else:
                    reply_text += f'\n\nПользователь без валидного никнейма. Telegram id: {user.user_id} (для связи через админку).'

                try:
                    await call.bot.send_message(chat_id=config.SIM_MANAGER_ID,
                                    text=reply_text,
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
                    await call.message.edit_reply_markup(
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
                    await call.message.answer(
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
                    await call.message.delete()
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
                    await call.message.answer(
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
                    await call.message.edit_text(
                                            text=reply_text,
                                            parse_mode='Markdown',
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
                    await call.message.delete()
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
                    await call.message.answer(
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
            user.curr_input = 's-phone'
            await sync_to_async(user.save)()

            question = await sync_to_async(TGText.objects.get)(slug='sim_phone_question', language=user_language)
            try:
                await call.message.edit_text(
                                text=question.text,
                                reply_markup=await new_keyboards.skip_sim_phone_keyboard(user_language),
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
            sim_card = await sync_to_async(user.sim_cards.first)()

            if sim_card and sim_card.circuit_id_collect is None: # and sim_card.debt >= config.SIM_DEBT_LIMIT
                reply = await sync_to_async(TGText.objects.get)(slug='collect_sim_money', language=user_language)

                try:
                    await call.message.edit_reply_markup(
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
                    await call.message.answer(
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
                    sim_card.pay_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()
                    sim_card.circuit_id_collect = stop_id
                    sim_card.circuit_api_collect = True
                else:
                    sim_card.circuit_api_collect = False

                await sync_to_async(sim_card.save)()

            else:
                try:
                    await call.message.delete()
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
                    await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
            await call.message.delete()
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
                user.curr_input = 's-address'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
                try:   
                    await call.message.answer(
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

        elif curr_input and curr_input == 's-name' and info == 'name':
            question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)
            try:
                await call.message.answer(
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
                await call.message.answer(
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
                await call.message.answer(
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
                await call.message.answer(
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
            await call.message.delete()
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

        if curr_input and curr_input == 'sim-fare' and user.addresses and fare and user.name and user.family_name:
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
                        '''
            data = await state.get_data()
            if user_entered_phone := data.get('phone'):
                phone_short = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                reply_text += f'\n*{phone_short.text}* {user_entered_phone}'

            reply_text += f'''\n\
                        \n*{fare_description.text}*\
                        \n{fare.description}\
                        \n*{fare_price.text}* {fare.price}₪/{short_month.text} {new_sim_tax.text}\
                        '''

            try:
                await call.message.answer(
                                text=reply_text,
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
                await call.message.answer(
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
            await call.message.delete()
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
                await call.message.answer(
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
                await call.message.answer(
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
    
    elif query == 'faq':
        questions = await sync_to_async(lambda: list(Question.objects.all()))()
        questions_text = ''

        for question in questions:
            if user_language.slug == 'uzb':
                questions_text += f'{question.order}. {question.question_uzb}\n\n'
            else:
                questions_text += f'{question.order}. {question.question_rus}\n\n'

        try:
            await call.message.edit_text(
                                text=questions_text,
                                parse_mode='Markdown',
                                reply_markup=await keyboards.questions_keyboard(user_language),
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

    elif query == 'question':
        order_num = int(call_data[1])
        try:
            question = await sync_to_async(Question.objects.get)(order=order_num)
        except:
            question = None
        
        if question:
            if user_language.slug == 'uzb':
                answer = question.answer_uzb.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('&nbsp;', '')
                reply = f'<b>{question.question_uzb}</b>\n\n{answer}'
            else:
                answer = question.answer_rus.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('&nbsp;', '')
                reply = f'<b>{question.question_rus}</b>\n\n{answer}'

            try:
                await call.message.edit_text(
                                    text=reply,
                                    parse_mode='HTML',
                                    reply_markup=await keyboards.back_faq_keyboard(user_language, question.rate),
                                    )
            except Exception as ex:
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='1',
                        main_user=user_id,
                        description=f'Не удалось отредактировать сообщение пользователя {user_id}.',
                    )
                except:
                    pass
    
    elif query == 'currentrate':
        current_rate_text = await sync_to_async(TGText.objects.get)(slug='current_rate', language=user_language)
        ils_rate = await sync_to_async(Rate.objects.get)(slug='usd-ils')
        
        try:
            await call.message.answer(
                        text=f'{current_rate_text.text} {ils_rate.rate} ₪/$',
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
                await call.message.delete()
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
                    await call.message.answer(
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
                    await call.message.answer(
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
        
        elif destination == 'main':
            reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)
            try:
                await call.message.edit_text(
                                    text=reply_text.text,
                                    parse_mode='Markdown',
                                    reply_markup=await keyboards.flight_or_parcel_keyboard(user_language),
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

        elif destination == 'faq':
            questions = await sync_to_async(lambda: list(Question.objects.all()))()
            questions_text = ''

            for question in questions:
                if user_language.slug == 'uzb':
                    questions_text += f'{question.order}. {question.question_uzb}\n\n'
                else:
                    questions_text += f'{question.order}. {question.question_rus}\n\n'

            try:
                await call.message.edit_text(
                                    text=questions_text,
                                    parse_mode='Markdown',
                                    reply_markup=await keyboards.questions_keyboard(user_language),
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
        
        elif destination == 'simpayoptions':
            try:
                await call.message.edit_reply_markup(
                                    reply_markup=await keyboards.sim_payment_options_keyboard(user_language),
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

    elif query == 's-refuse':
        user.curr_input = None
        await sync_to_async(user.save)()

        try:
            await call.message.edit_reply_markup(
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
            await call.message.answer(
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
                await call.message.edit_reply_markup(
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
                await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
                    await call.message.edit_reply_markup(
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
                        await call.message.delete()
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
                        await call.message.answer(
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
                        await call.message.answer(
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
                    await call.message.delete()
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
                    await call.message.answer(
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
            if period != 'date':
                if period == 'week':
                    days = 7
                    debt = sim_card.debt
                elif period == 'month':
                    days = 31
                    fare_price = await sync_to_async(lambda: sim_card.fare.price)()
                    debt = sim_card.debt + fare_price
                else:
                    planing_payment_date = datetime.datetime.strptime(period, '%d.%m.%Y').date()
                    days = (planing_payment_date - (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()).days
                    if sim_card.next_payment <= planing_payment_date:
                        fare_price = await sync_to_async(lambda: sim_card.fare.price)()
                        debt = sim_card.debt + fare_price
                    else:
                        debt = sim_card.debt


                sim_card.pay_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3) + datetime.timedelta(days=days)).date()
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
                    await call.message.edit_reply_markup(
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
                    await call.message.answer(
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
                    await call.message.edit_reply_markup(
                                    reply_markup=await keyboards.payments_dates_keyboards(user_language),
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
                await call.message.delete()
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
                await call.message.answer(
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
                await call.message.edit_reply_markup(
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
                await call.message.answer(
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
                await call.message.delete()
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
                await call.message.answer(
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
    
    elif query == 'sim-pay-handwrite':
        try:
            user.curr_input = f'sim-payment-date'
            await sync_to_async(user.save)()

            question = await sync_to_async(TGText.objects.get)(slug='sim_payment_date', language=user_language)
            await call.message.edit_text(
                        text=question.text,
                        parse_mode='Markdown',
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
