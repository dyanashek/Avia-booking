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

from django.core.files.base import ContentFile
from filer.models import Image, Folder
from django.db.models import Q

from core.models import TGUser, TGText, Language, Parcel, Flight, Route, Day, ParcelVariation

import config
import keyboards
import functions
import utils


bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_message(message: types.Message):
    '''Handles start command.'''

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

    user_language = await sync_to_async(lambda: user.language)()
    if user_language:
        reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)
        await bot.send_message(chat_id=user_id,
                            text=reply_text.text,
                            reply_markup=await keyboards.flight_or_parcel_keyboard(user_language),
                            parse_mode='Markdown',
                            )

    else:
        choose_language = await sync_to_async(TGText.objects.get)(slug='choose_language')

        await bot.send_message(chat_id=user_id,
                         text=choose_language.text,
                         reply_markup=await keyboards.choose_language_keyboard(),
                         parse_mode='Markdown',
                         )


@dp.message(Command("language"))
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

    await bot.send_message(chat_id=user_id,
                        text=choose_language.text,
                        reply_markup=await keyboards.choose_language_keyboard(),
                        parse_mode='Markdown',
                        )


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
        await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=welcome_text.text,
                                parse_mode='Markdown',
                                )
        
        await bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=await keyboards.flight_or_parcel_keyboard(language),
                                        )
    
    elif query == 'flight':
        await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
        await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

        flight = Flight(user=user)
        await sync_to_async(flight.save)()
        user.curr_input = 'flight_route'
        await sync_to_async(user.save)()

        choose_route = await sync_to_async(TGText.objects.get)(slug='choose_route', language=user_language)

        await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=choose_route.text,
                                parse_mode='Markdown',
                                )
        
        await bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=await keyboards.route_keyboard(),
                                        )
    
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
            await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=choose_flight_type.text,
                                    parse_mode='Markdown',
                                    )
            
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=await keyboards.flight_type_keyboard(user_language),
                                            )

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            bot.send_message(chat_id=chat_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )

    elif query == 'flighttype':
        flight_type = call_data[1]
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        if flight and curr_input and curr_input == 'flight_type':
            flight.type = flight_type
            await sync_to_async(flight.save)()
            user.curr_input = 'flight_departure'
            await sync_to_async(user.save)()

            departure_text = await sync_to_async(TGText.objects.get)(slug='choose_departure_month', language=user_language)
            await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=departure_text.text,
                                    parse_mode='Markdown',
                                    )
            
            await bot.edit_message_reply_markup(chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year, user_language),
                                            )

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=chat_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )
    
    elif query == 'month':
        direction = call_data[1]
        year = int(call_data[2])
        month = int(call_data[3])

        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        if flight and direction == 'departure' and curr_input and curr_input == 'flight_departure':
            departure_days = await sync_to_async(lambda: list(flight.route.days.filter(Q(day__year=year) & Q(day__month=month) & Q(day__gte=datetime.date.today()))))()
            if departure_days:
                departure_day = await sync_to_async(TGText.objects.get)(slug='choose_departure_day', language=user_language)
                await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=departure_day.text,
                                    parse_mode='Markdown',
                                    )
            
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=await keyboards.choose_day_keyboard(departure_days, user_language),
                                                )

            else:
                no_flight = await sync_to_async(TGText.objects.get)(slug='no_flights', language=user_language)
                await bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=no_flight.text,
                                show_alert=True,
                                )

        elif flight and direction == 'arrival' and curr_input and curr_input == 'flight_arrival':
            arrival_days = await sync_to_async(lambda: list(flight.route.opposite.days.filter(Q(day__year=year) & Q(day__month=month) & Q(day__gte=datetime.date.today()))))()
            if arrival_days:
                arrival_day = await sync_to_async(TGText.objects.get)(slug='choose_arrival_day', language=user_language)
                await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=arrival_day.text,
                                    parse_mode='Markdown',
                                    )
            
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=await keyboards.choose_day_keyboard(arrival_days, user_language, 'arrival'),
                                                )

            else:
                no_flight = await sync_to_async(TGText.objects.get)(slug='no_flights', language=user_language)
                await bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=no_flight.text,
                                show_alert=True,
                                )

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=chat_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )

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
                await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=arrival_text.text,
                                        parse_mode='Markdown',
                                        )
                
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year, user_language, 'arrival'),
                                                )


            elif flight.type == 'oneway':
                user.curr_input = 'passport'
                await sync_to_async(user.save)()

                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
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

                    await bot.send_photo(chat_id=user_id,
                            caption=reply_text,
                            photo=user.passport_photo_id,
                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
                            parse_mode='Markdown',
                            disable_notification=False,
                            )

                else:
                    passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=passport_request.text,
                            parse_mode='Markdown',
                            )
                
        elif flight and direction == 'arrival' and curr_input and curr_input == 'flight_arrival':
            day = await sync_to_async(Day.objects.filter(id=date_id).first)()
            flight.arrival_date = day.day
            await sync_to_async(flight.save)()
            user.curr_input = 'passport'
            await sync_to_async(user.save)()

            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
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

                await bot.send_photo(chat_id=user_id,
                        caption=reply_text,
                        photo=user.passport_photo_id,
                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
                        parse_mode='Markdown',
                        disable_notification=False,
                        )

            else:
                passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=passport_request.text,
                        parse_mode='Markdown',
                        )

        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=chat_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )
    
    elif query == 'curryear':
        direction = call_data[1]

        await bot.edit_message_reply_markup(chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year, user_language, direction),
                                    )
    
    elif query == 'nextyear':
        direction = call_data[1]

        await bot.edit_message_reply_markup(chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=await keyboards.choose_month_keyboard(datetime.date.today().year + 1, user_language, direction),
                                    )

    elif query == 'parcel':
        await sync_to_async(Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)
        await sync_to_async(Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update)(complete=False)

        parcel = Parcel(user=user)
        await sync_to_async(parcel.save)()
        
        user.curr_input = 'parcel_type'
        await sync_to_async(user.save)()

        choose = await sync_to_async(TGText.objects.get)(slug='choose_options', language=user_language)
        await bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=choose.text,
                                parse_mode='Markdown',
                                )
        
        await bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=await keyboards.parcel_types_keyboard(user_language),
                                        )
    
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
                pass

            question = await sync_to_async(TGText.objects.get)(slug='fio_receiver_question', language=user_language)
            await bot.send_message(chat_id=chat_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )
            
        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=chat_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )

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
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )
        
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

                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('familyname', user_language),
                                                    )

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

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

                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('passportnum', user_language),
                                                    )

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

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

                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('sex', user_language),
                                                    )

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            reply_markup=await keyboards.sex_keyboard(user_language),
                            parse_mode='Markdown',
                            )

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

                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('birthdate', user_language),
                                                    )

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

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

                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('startdate', user_language),
                                                    )

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

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

                    await bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    await bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('enddate', user_language),
                                                    )

                else:
                    try:
                        await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

            elif info == 'enddate':
                user.curr_input = 'phone'
                await sync_to_async(user.save)()

                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                phone_question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)
                await bot.send_message(chat_id=chat_id,
                        text=phone_question.text,
                        parse_mode='Markdown',
                        reply_markup=await keyboards.request_phone_keyboard(user_language),
                        )
            
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
                    await sync_to_async(parcel.save)()

                await sync_to_async(user.save)()

                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=InlineKeyboardBuilder().as_markup(),
                                                )
                
                reply_text = await sync_to_async(TGText.objects.get)(slug='contact_soon', language=user_language)
                await bot.send_message(chat_id=chat_id,
                        text=reply_text.text,
                        parse_mode='Markdown',
                        )
                
                if flight:
                    try:
                        await bot.send_message(chat_id=config.MANAGER_ID,
                                        text='Новая заявка *(перелет)*',
                                        parse_mode='Markdown',
                                        )
                    except:
                        pass
                elif parcel:
                    try:
                        await bot.send_message(chat_id=config.MANAGER_ID,
                                        text='Новая заявка *(посылка)*',
                                        parse_mode='Markdown',
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
                    pass

                await bot.send_photo(chat_id=user_id,
                               caption=reply_text,
                               photo=photo_id,
                               reply_markup=await keyboards.confirm_or_hand_write_keyboard('confirmation', user_language),
                               parse_mode='Markdown',
                               disable_notification=False,
                               )
        
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
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )
        
        else:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            if info == 'name':
                question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )

            elif info == 'familyname':
                question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )

            elif info == 'passportnum':
                question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )

            elif info == 'sex':
                question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        reply_markup=await keyboards.sex_keyboard(user_language),
                        parse_mode='Markdown',
                        )

            elif info == 'birthdate':
                question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )

            elif info == 'startdate':
                question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )

            elif info == 'enddate':
                question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)
                await bot.send_message(chat_id=chat_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )
            
            elif info == 'passport':
                passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=passport_request.text,
                        parse_mode='Markdown',
                        )

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
                pass

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )
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

                await bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=reply_text,
                                    parse_mode='Markdown',
                                    )
            
                await bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('birthdate', user_language),
                                                )

            else:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)

                await bot.send_message(chat_id=user_id,
                        text=question.text,
                        parse_mode='Markdown',
                        )
            
    elif query == 'cancel':
        user.curr_input = None
        await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
        await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)

        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass

        reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)

        await bot.send_message(chat_id=chat_id,
                            text=reply_text.text,
                            reply_markup=await keyboards.flight_or_parcel_keyboard(user_language),
                            parse_mode='Markdown',
                            )


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    photo = message.photo[-1].file_id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
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
            await bot.send_message(chat_id=user_id,
                            text=error.text,
                            parse_mode='Markdown',
                            )

        else:
            counter = 0
            try:
                file_info = await bot.get_file(photo)
                downloaded_file = await bot.download_file(file_info.file_path)
                
                photo_info = await functions.parse_passport(downloaded_file)
            except Exception as ex:
                counter = config.PARSE_COUNT
                photo_info = [None, None, None, None, None, None, None]


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
                    print(ex)
                    passport = None
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

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('name', user_language),
                            parse_mode='Markdown',
                            )

                else:
                    name_question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=name_question.text,
                            parse_mode='Markdown',
                            )

            else:
                wrong_passport = await sync_to_async(TGText.objects.get)(slug='wrong_passport', language=user_language)
                await bot.send_message(chat_id=user_id,
                                text=wrong_passport.text,
                                parse_mode='Markdown',
                                )


@dp.message(F.contact)
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
            await bot.send_message(chat_id=user_id,
                            text=error,
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            )
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
            await bot.send_message(chat_id=chat_id,
                            text=question.text,
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            disable_notification=True,
                            )


@dp.message(F.text)
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
    curr_input = user.curr_input
    input_info = await utils.escape_markdown(message.text)

    if curr_input:
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if (flight and parcel) or (not flight and not parcel):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            await bot.send_message(chat_id=user_id,
                            text=error.text,
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            )
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

                    await bot.send_message(chat_id=chat_id,
                                    text=reply_text,
                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('familyname', user_language),
                                    parse_mode='Markdown',
                                    )

                else:
                    question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

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

                    await bot.send_message(chat_id=chat_id,
                                    text=reply_text,
                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('passportnum', user_language),
                                    parse_mode='Markdown',
                                    )

                else:
                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

                    await bot.send_message(chat_id=user_id,
                            text=question.text,
                            parse_mode='Markdown',
                            )

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

                        await bot.send_message(chat_id=chat_id,
                                            text=reply_text,
                                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('sex', user_language),
                                            parse_mode='Markdown',
                                            )

                    else:
                        question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                reply_markup=await keyboards.sex_keyboard(user_language),
                                parse_mode='Markdown',
                                )

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

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

                        await bot.send_message(chat_id=chat_id,
                                            text=reply_text,
                                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('startdate', user_language),
                                            parse_mode='Markdown',
                                            )

                    else:
                        question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

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

                        await bot.send_message(chat_id=chat_id,
                                            text=reply_text,
                                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('enddate', user_language),
                                            parse_mode='Markdown',
                                            )

                    else:
                        question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)

                        await bot.send_message(chat_id=user_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
                
                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

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
                    await bot.send_message(chat_id=chat_id,
                            text=phone_question.text,
                            parse_mode='Markdown',
                            reply_markup=await keyboards.request_phone_keyboard(user_language),
                            )

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

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
                    await bot.send_message(chat_id=chat_id,
                            text=question.text,
                            reply_markup=types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            )
                
                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'address':
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

                await bot.send_photo(chat_id=user_id,
                               caption=reply_text,
                               photo=photo_id,
                               reply_markup=await keyboards.confirm_or_hand_write_keyboard('confirmation', user_language),
                               parse_mode='Markdown',
                               disable_notification=False,
                               )
        
            elif parcel and curr_input == 'fio_receiver':
                parcel.fio_receiver = input_info
                await sync_to_async(parcel.save)()

                user.curr_input = 'contains'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='contains_question', language=user_language)
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )
            
            elif parcel and curr_input == 'contains':
                parcel.items_list = input_info
                await sync_to_async(parcel.save)()

                user.curr_input = 'phone_receiver'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='phone_receiver_question', language=user_language)
                await bot.send_message(chat_id=chat_id,
                                text=question.text,
                                parse_mode='Markdown',
                                )

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

                        await bot.send_photo(chat_id=user_id,
                                caption=reply_text,
                                photo=user.passport_photo_id,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
                                )

                    else:
                        passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                        await bot.send_message(chat_id=user_id,
                                text=passport_request.text,
                                parse_mode='Markdown',
                                )

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='phone_receiver_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    await bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())