import os
import datetime

import django
import telebot

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


bot = telebot.TeleBot(config.TELEGRAM_TOKEN)


@bot.message_handler(commands=['start'])
def start_message(message):
    '''Handles start command.'''

    user_id = str(message.from_user.id)
    username = message.from_user.username
    if not username:
        username = None

    user, _ = TGUser.objects.get_or_create(user_id=user_id)
    user.username = username
    user.curr_input = None
    user.save()

    Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)
    Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)

    if user.language:
        reply_text = TGText.objects.get(slug='welcome', language=user.language).text
        bot.send_message(chat_id=user_id,
                            text=reply_text,
                            reply_markup=keyboards.flight_or_parcel_keyboard(user.language),
                            parse_mode='Markdown',
                            )

    else:
        choose_language = TGText.objects.get(slug='choose_language').text

        bot.send_message(chat_id=user_id,
                         text=choose_language,
                         reply_markup=keyboards.choose_language_keyboard(),
                         parse_mode='Markdown',
                         )


@bot.message_handler(commands=['language'])
def language_message(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    if not username:
        username = None

    user, _ = TGUser.objects.get_or_create(user_id=user_id)
    user.username = username
    user.curr_input = None
    user.save()

    Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)
    Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)

    choose_language = TGText.objects.get(slug='choose_language').text

    bot.send_message(chat_id=user_id,
                        text=choose_language,
                        reply_markup=keyboards.choose_language_keyboard(),
                        parse_mode='Markdown',
                        )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Handles queries from inline keyboards."""

    # getting message's and user's ids
    message_id = call.message.id
    chat_id = call.message.chat.id
    user_id = str(call.from_user.id)
    username = call.from_user.username

    user = TGUser.objects.get(user_id=user_id)
    if username:
        user.username = username
        user.save()

    user_language = user.language
    curr_input = user.curr_input
    call_data = call.data.split('_')
    query = call_data[0]

    if query == 'language':
        Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)
        Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)

        language_id = int(call_data[1])
        language = Language.objects.get(id=language_id)
        user.language = language
        user.save()

        welcome_text = TGText.objects.get(slug='welcome', language=language).text
        bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=welcome_text,
                                parse_mode='Markdown',
                                )
        
        bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=keyboards.flight_or_parcel_keyboard(language),
                                        )
    
    elif query == 'flight':
        Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)
        Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)

        flight = Flight(user=user)
        flight.save()
        user.curr_input = 'flight_route'
        user.save()

        choose_route = TGText.objects.get(slug='choose_route', language=user_language).text
        bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=choose_route,
                                parse_mode='Markdown',
                                )
        
        bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=keyboards.route_keyboard(),
                                        )
    
    elif query == 'route':
        route_id = int(call_data[1])
        route = Route.objects.filter(id=route_id).first()
        flight = Flight.objects.filter(user=user, complete__isnull=True).first()

        if route and flight and curr_input and curr_input == 'flight_route':
            flight.route = route
            flight.save()
            user.curr_input = 'flight_type'
            user.save()

            choose_flight_type = TGText.objects.get(slug='choose_options', language=user_language).text
            bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=choose_flight_type,
                                    parse_mode='Markdown',
                                    )
            
            bot.edit_message_reply_markup(chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=keyboards.flight_type_keyboard(user_language),
                                            )

        else:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=error,
                            parse_mode='Markdown',
                            )

    elif query == 'flighttype':
        flight_type = call_data[1]
        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        if flight and curr_input and curr_input == 'flight_type':
            flight.type = flight_type
            flight.save()
            user.curr_input = 'flight_departure'
            user.save()

            departure_text = TGText.objects.get(slug='choose_departure_month', language=user_language).text
            bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=departure_text,
                                    parse_mode='Markdown',
                                    )
            
            bot.edit_message_reply_markup(chat_id=chat_id,
                                            message_id=message_id,
                                            reply_markup=keyboards.choose_month_keyboard(datetime.date.today().year, user_language),
                                            )

        else:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=error,
                            parse_mode='Markdown',
                            )
    
    elif query == 'month':
        direction = call_data[1]
        year = int(call_data[2])
        month = int(call_data[3])

        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        if flight and direction == 'departure' and curr_input and curr_input == 'flight_departure':
            departure_days = flight.route.days.filter(Q(day__year=year) & Q(day__month=month) & Q(day__gte=datetime.date.today())).all()
            if departure_days:
                departure_day = TGText.objects.get(slug='choose_departure_day', language=user_language).text
                bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=departure_day,
                                    parse_mode='Markdown',
                                    )
            
                bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=keyboards.choose_day_keyboard(departure_days, user_language),
                                                )

            else:
                no_flight = TGText.objects.get(slug='no_flights', language=user.language).text
                bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=no_flight,
                                show_alert=True,
                                )

        elif flight and direction == 'arrival' and curr_input and curr_input == 'flight_arrival':
            arrival_days = flight.route.opposite.days.filter(Q(day__year=year) & Q(day__month=month) & Q(day__gte=datetime.date.today())).all()
            if arrival_days:
                arrival_day = TGText.objects.get(slug='choose_arrival_day', language=user_language).text
                bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=arrival_day,
                                    parse_mode='Markdown',
                                    )
            
                bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=keyboards.choose_day_keyboard(arrival_days, user_language, 'arrival'),
                                                )

            else:
                no_flight = TGText.objects.get(slug='no_flights', language=user.language).text
                bot.answer_callback_query(
                                callback_query_id=call.id,
                                text=no_flight,
                                show_alert=True,
                                )

        else:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=error,
                            parse_mode='Markdown',
                            )

    elif query == 'day':
        direction = call_data[1]
        date_id = int(call_data[2])
        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        if flight and direction == 'departure' and curr_input and curr_input == 'flight_departure':
            flight.departure_date = Day.objects.filter(id=date_id).first().day
            flight.save()
            if flight.type == 'roundtrip':
                user.curr_input = 'flight_arrival'
                user.save()

                arrival_text = TGText.objects.get(slug='choose_arrival_month', language=user_language).text
                bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=arrival_text,
                                        parse_mode='Markdown',
                                        )
                
                bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=keyboards.choose_month_keyboard(datetime.date.today().year, user_language, 'arrival'),
                                                )


            elif flight.type == 'oneway':
                user.curr_input = 'passport'
                user.save()

                try:
                    bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
                user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                    reuse = TGText.objects.get(slug='reuse', language=user_language).text
                    name = TGText.objects.get(slug='name', language=user_language).text
                    family_name = TGText.objects.get(slug='familyname', language=user_language).text
                    passport = TGText.objects.get(slug='passport', language=user_language).text
                    sex = TGText.objects.get(slug='sex', language=user_language).text
                    birth_date = TGText.objects.get(slug='birth', language=user_language).text
                    start_date = TGText.objects.get(slug='start', language=user_language).text
                    end_date = TGText.objects.get(slug='end', language=user_language).text
                    phone = TGText.objects.get(slug='phone', language=user_language).text
                    address = TGText.objects.get(slug='address', language=user_language).text

                    photo_id = user.passport_photo_id

                    reply_text = f'{reuse}\n'
                    
                    reply_text += f'\n*{name}* {user.name}'
                    reply_text += f'\n*{family_name}* {user.family_name}'
                    reply_text += f'\n*{passport}* {user.passport_number}'
                    reply_text += f'\n*{sex}* {user.sex}'
                    reply_text += f'\n*{birth_date}* {user.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date}* {user.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date}* {user.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone}* {user.phone}'
                    reply_text += f'\n*{address}* {user.addresses}'

                    bot.send_photo(chat_id=user_id,
                            caption=reply_text,
                            photo=photo_id,
                            reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                            parse_mode='Markdown',
                            disable_notification=False,
                            )

                else:
                    passport_request = TGText.objects.get(slug='passport_photo_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=passport_request,
                            parse_mode='Markdown',
                            )
                
        elif flight and direction == 'arrival' and curr_input and curr_input == 'flight_arrival':
            flight.arrival_date = Day.objects.filter(id=date_id).first().day
            flight.save()
            user.curr_input = 'passport'
            user.save()

            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
            user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                reuse = TGText.objects.get(slug='reuse', language=user_language).text
                name = TGText.objects.get(slug='name', language=user_language).text
                family_name = TGText.objects.get(slug='familyname', language=user_language).text
                passport = TGText.objects.get(slug='passport', language=user_language).text
                sex = TGText.objects.get(slug='sex', language=user_language).text
                birth_date = TGText.objects.get(slug='birth', language=user_language).text
                start_date = TGText.objects.get(slug='start', language=user_language).text
                end_date = TGText.objects.get(slug='end', language=user_language).text
                phone = TGText.objects.get(slug='phone', language=user_language).text
                address = TGText.objects.get(slug='address', language=user_language).text

                photo_id = user.passport_photo_id

                reply_text = f'{reuse}\n'
                
                reply_text += f'\n*{name}* {user.name}'
                reply_text += f'\n*{family_name}* {user.family_name}'
                reply_text += f'\n*{passport}* {user.passport_number}'
                reply_text += f'\n*{sex}* {user.sex}'
                reply_text += f'\n*{birth_date}* {user.birth_date.strftime("%d.%m.%Y")}'
                reply_text += f'\n*{start_date}* {user.start_date.strftime("%d.%m.%Y")}'
                reply_text += f'\n*{end_date}* {user.end_date.strftime("%d.%m.%Y")}'
                reply_text += f'\n*{phone}* {user.phone}'
                reply_text += f'\n*{address}* {user.addresses}'

                bot.send_photo(chat_id=user_id,
                        caption=reply_text,
                        photo=photo_id,
                        reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                        parse_mode='Markdown',
                        disable_notification=False,
                        )

            else:
                passport_request = TGText.objects.get(slug='passport_photo_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=passport_request,
                        parse_mode='Markdown',
                        )

        else:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=error,
                            parse_mode='Markdown',
                            )
    
    elif query == 'curryear':
        direction = call_data[1]

        bot.edit_message_reply_markup(chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=keyboards.choose_month_keyboard(datetime.date.today().year, user_language, direction),
                                    )
    
    elif query == 'nextyear':
        direction = call_data[1]

        bot.edit_message_reply_markup(chat_id=chat_id,
                                    message_id=message_id,
                                    reply_markup=keyboards.choose_month_keyboard(datetime.date.today().year + 1, user_language, direction),
                                    )

    elif query == 'parcel':
        Flight.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)
        Parcel.objects.filter(Q(user=user) & Q(complete__isnull=True)).update(complete=False)

        parcel = Parcel(user=user)
        parcel.save()
        
        user.curr_input = 'parcel_type'
        user.save()

        choose = TGText.objects.get(slug='choose_options', language=user_language).text
        bot.edit_message_text(chat_id=chat_id,
                                message_id=message_id,
                                text=choose,
                                parse_mode='Markdown',
                                )
        
        bot.edit_message_reply_markup(chat_id=chat_id,
                                        message_id=message_id,
                                        reply_markup=keyboards.parcel_types_keyboard(user_language),
                                        )
    
    elif query == 'parceltype':
        parcel_type_id = int(call_data[1])
        parcel_type = ParcelVariation.objects.filter(id=parcel_type_id).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()
        if parcel and curr_input and curr_input == 'parcel_type':
            parcel.variation = parcel_type
            parcel.save()
            user.curr_input = 'fio_receiver'
            user.save()

            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            question = TGText.objects.get(slug='fio_receiver_question', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=question,
                            parse_mode='Markdown',
                            )
            
        else:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=error,
                            parse_mode='Markdown',
                            )

    elif query == 'confirm':
        info = call_data[1]

        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()

        if (flight and parcel) or (not flight and not parcel) or (not curr_input) or (curr_input != info):
            Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
            Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)
            user.curr_input = None
            user.save()

            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=user_id,
                            text=error,
                            parse_mode='Markdown',
                            )
        
        else:
            if info == 'name':
                user.curr_input = 'familyname'
                user.save()

                if flight:
                    family_name = flight.family_name
                elif parcel:
                    family_name = parcel.family_name
                
                if family_name:
                    confirm_text = TGText.objects.get(slug='familyname_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{family_name}*?'

                    bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                    )

                else:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = TGText.objects.get(slug='familyname_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif info == 'familyname':
                user.curr_input = 'passportnum'
                user.save()

                if flight:
                    passport_num = flight.passport_number
                elif parcel:
                    passport_num = parcel.passport_number
                
                if passport_num:
                    confirm_text = TGText.objects.get(slug='passport_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{passport_num}*?'

                    bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                    )

                else:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = TGText.objects.get(slug='passport_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif info == 'passportnum':
                user.curr_input = 'sex'
                user.save()

                if flight:
                    sex = flight.sex
                elif parcel:
                    sex = parcel.sex
                
                if sex:
                    confirm_text = TGText.objects.get(slug='sex_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{sex}*?'

                    bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                    )

                else:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = TGText.objects.get(slug='sex_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            reply_markup=keyboards.sex_keyboard(user_language),
                            parse_mode='Markdown',
                            )

            elif info == 'sex':
                user.curr_input = 'birthdate'
                user.save()

                if flight:
                    birth_date = flight.birth_date
                elif parcel:
                    birth_date = parcel.birth_date
                
                if birth_date:
                    birth_date = birth_date.strftime('%d.%m.%Y')

                    confirm_text = TGText.objects.get(slug='birth_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{birth_date}*?'

                    bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                    )

                else:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = TGText.objects.get(slug='birth_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif info == 'birthdate':
                user.curr_input = 'startdate'
                user.save()

                if flight:
                    start_date = flight.start_date
                elif parcel:
                    start_date = parcel.start_date
                
                if start_date:
                    start_date = start_date.strftime('%d.%m.%Y')

                    confirm_text = TGText.objects.get(slug='start_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{start_date}*?'

                    bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                    )

                else:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = TGText.objects.get(slug='start_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif info == 'startdate':
                user.curr_input = 'enddate'
                user.save()

                if flight:
                    end_date = flight.end_date
                elif parcel:
                    end_date = parcel.end_date
                
                if end_date:
                    end_date = end_date.strftime('%d.%m.%Y')

                    confirm_text = TGText.objects.get(slug='end_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{end_date}*?'

                    bot.edit_message_text(chat_id=chat_id,
                                        message_id=message_id,
                                        text=reply_text,
                                        parse_mode='Markdown',
                                        )
                
                    bot.edit_message_reply_markup(chat_id=chat_id,
                                                    message_id=message_id,
                                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                    )

                else:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=message_id)
                    except:
                        pass

                    question = TGText.objects.get(slug='end_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif info == 'enddate':
                user.curr_input = 'phone'
                user.save()

                try:
                    bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                phone_question = TGText.objects.get(slug='phone_question', language=user_language).text
                bot.send_message(chat_id=chat_id,
                        text=phone_question,
                        parse_mode='Markdown',
                        reply_markup=keyboards.request_phone_keyboard(user_language),
                        )
            
            elif info == 'confirmation':
                user.curr_input = None

                if flight:
                    flight.complete = True 
                    flight.save()
                    user.name = flight.name
                    user.family_name = flight.family_name
                    user.passport_number = flight.passport_number
                    user.sex = flight.sex
                    user.birth_date = flight.birth_date
                    user.start_date = flight.start_date
                    user.end_date = flight.end_date
                    user.passport_photo_user = flight.passport_photo_flight
                    user.passport_photo_id = flight.passport_photo_id
                    user.phone = flight.phone
                    user.addresses = flight.address

                elif parcel:
                    parcel.complete = True 
                    parcel.save()
                    user.name = parcel.name
                    user.family_name = parcel.family_name
                    user.passport_number = parcel.passport_number
                    user.sex = parcel.sex
                    user.birth_date = parcel.birth_date
                    user.start_date = parcel.start_date
                    user.end_date = parcel.end_date
                    user.passport_photo_user = parcel.passport_photo_parcel
                    user.passport_photo_id = parcel.passport_photo_id
                    user.phone = parcel.phone
                    user.addresses = parcel.address
                
                user.save()

                bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=telebot.types.InlineKeyboardMarkup(),
                                                )
                
                reply_text = TGText.objects.get(slug='contact_soon', language=user_language).text
                bot.send_message(chat_id=chat_id,
                        text=reply_text,
                        parse_mode='Markdown',
                        )
                
                if flight:
                    try:
                        bot.send_message(chat_id=config.MANAGER_ID,
                                        text='Новая заявка *(перелет)*',
                                        parse_mode='Markdown',
                                        )
                    except:
                        pass
                elif parcel:
                    try:
                        bot.send_message(chat_id=config.MANAGER_ID,
                                        text='Новая заявка *(посылка)*',
                                        parse_mode='Markdown',
                                        )
                    except:
                        pass
            
            elif info == 'passport':
                confirm_application = TGText.objects.get(slug='confirm_application', language=user_language).text
                name = TGText.objects.get(slug='name', language=user_language).text
                family_name = TGText.objects.get(slug='familyname', language=user_language).text
                passport = TGText.objects.get(slug='passport', language=user_language).text
                sex = TGText.objects.get(slug='sex', language=user_language).text
                birth_date = TGText.objects.get(slug='birth', language=user_language).text
                start_date = TGText.objects.get(slug='start', language=user_language).text
                end_date = TGText.objects.get(slug='end', language=user_language).text
                phone = TGText.objects.get(slug='phone', language=user_language).text
                address = TGText.objects.get(slug='address', language=user_language).text

                user.curr_input = 'confirmation'
                user.save()

                if flight:
                    flight.name = user.name
                    flight.family_name = user.family_name
                    flight.passport_number = user.passport_number
                    flight.sex = user.sex
                    flight.birth_date = user.birth_date
                    flight.start_date = user.start_date
                    flight.end_date = user.end_date
                    flight.passport_photo_flight = user.passport_photo_user
                    flight.passport_photo_id = user.passport_photo_id
                    flight.phone = user.phone
                    flight.address = user.addresses
                    flight.save()

                    route = TGText.objects.get(slug='route', language=user_language).text
                    flight_type = TGText.objects.get(slug='type_flight', language=user_language).text
                    departure_date = TGText.objects.get(slug='departure', language=user_language).text
                    arrival_date = TGText.objects.get(slug='arrival', language=user_language).text

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = TGText.objects.get(slug='oneway_button', language=user_language).text.lower()
                    else:
                        flight_type_text = TGText.objects.get(slug='roundtrip_button', language=user_language).text.lower()

                    reply_text = f'{confirm_application}\n'
                    reply_text += f'\n*{route}* {flight.route.route}'
                    reply_text += f'\n*{flight_type}* {flight_type_text}'
                    reply_text += f'\n*{departure_date}* {flight.departure_date}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date}* {flight.arrival_date}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name}* {flight.name}'
                    reply_text += f'\n*{family_name}* {flight.family_name}'
                    reply_text += f'\n*{passport}* {flight.passport_number}'
                    reply_text += f'\n*{sex}* {flight.sex}'
                    reply_text += f'\n*{birth_date}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone}* {flight.phone}'
                    reply_text += f'\n*{address}* {flight.address}'

                elif parcel:
                    parcel.name = user.name
                    parcel.family_name = user.family_name
                    parcel.passport_number = user.passport_number
                    parcel.sex = user.sex
                    parcel.birth_date = user.birth_date
                    parcel.start_date = user.start_date
                    parcel.end_date = user.end_date
                    parcel.passport_photo_parcel = user.passport_photo_user
                    parcel.passport_photo_id = user.passport_photo_id
                    parcel.phone = user.phone
                    parcel.address = user.addresses
                    parcel.save()

                    parcel_type = TGText.objects.get(slug='type_parcel', language=user_language).text
                    items_list = TGText.objects.get(slug='contains', language=user_language).text
                    fio_receiver = TGText.objects.get(slug='fio_receiver', language=user_language).text
                    phone_receiver = TGText.objects.get(slug='receiver_phone', language=user_language).text

                    photo_id = parcel.passport_photo_id

                    reply_text = f'{confirm_application}\n'
                    reply_text += f'\n*{parcel_type}* {parcel.variation.name}'
                    reply_text += f'\n*{items_list}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name}* {parcel.name}'
                    reply_text += f'\n*{family_name}* {parcel.family_name}'
                    reply_text += f'\n*{passport}* {parcel.passport_number}'
                    reply_text += f'\n*{sex}* {parcel.sex}'
                    reply_text += f'\n*{birth_date}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone}* {parcel.phone}'
                    reply_text += f'\n*{address}* {parcel.address}'

                bot.send_photo(chat_id=user_id,
                               caption=reply_text,
                               photo=photo_id,
                               reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                               parse_mode='Markdown',
                               disable_notification=False,
                               )
        
    elif query == 'hand':
        info = call_data[1]

        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()

        if (flight and parcel) or (not flight and not parcel) or (not curr_input) or (curr_input != info):
            Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
            Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)
            user.curr_input = None
            user.save()

            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=user_id,
                            text=error,
                            parse_mode='Markdown',
                            )
        
        else:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            if info == 'name':
                question = TGText.objects.get(slug='name_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        parse_mode='Markdown',
                        )

            elif info == 'familyname':
                question = TGText.objects.get(slug='familyname_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        parse_mode='Markdown',
                        )

            elif info == 'passportnum':
                question = TGText.objects.get(slug='passport_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        parse_mode='Markdown',
                        )

            elif info == 'sex':
                question = TGText.objects.get(slug='sex_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        reply_markup=keyboards.sex_keyboard(user_language),
                        parse_mode='Markdown',
                        )

            elif info == 'birthdate':
                question = TGText.objects.get(slug='birth_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        parse_mode='Markdown',
                        )

            elif info == 'startdate':
                question = TGText.objects.get(slug='start_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        parse_mode='Markdown',
                        )

            elif info == 'enddate':
                phone_question = TGText.objects.get(slug='phone_question', language=user_language).text
                bot.send_message(chat_id=chat_id,
                        text=phone_question,
                        parse_mode='Markdown',
                        reply_markup=keyboards.request_phone_keyboard(user_language),
                        )
            
            elif info == 'passport':
                passport_request = TGText.objects.get(slug='passport_photo_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=passport_request,
                        parse_mode='Markdown',
                        )

    elif query == 'sex':
        sex = call_data[1]

        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()

        if (flight and parcel) or (not flight and not parcel) or (not curr_input) or (curr_input != 'sex'):
            Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
            Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)
            user.curr_input = None
            user.save()

            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=user_id,
                            text=error,
                            parse_mode='Markdown',
                            )
        else:
            user.curr_input = 'birthdate'
            user.save()

            if flight:
                flight.sex = sex
                flight.save()
                birth_date = flight.birth_date
            elif parcel:
                parcel.sex = sex
                parcel.save()
                birth_date = parcel.birth_date
            
            if birth_date:
                birth_date = birth_date.strftime('%d.%m.%Y')

                confirm_text = TGText.objects.get(slug='birth_correct_question', language=user_language).text
                reply_text = f'{confirm_text} *{birth_date}*?'

                bot.edit_message_text(chat_id=chat_id,
                                    message_id=message_id,
                                    text=reply_text,
                                    parse_mode='Markdown',
                                    )
            
                bot.edit_message_reply_markup(chat_id=chat_id,
                                                message_id=message_id,
                                                reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                                )

            else:
                try:
                    bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass

                question = TGText.objects.get(slug='birth_question', language=user_language).text

                bot.send_message(chat_id=user_id,
                        text=question,
                        parse_mode='Markdown',
                        )
            
    elif query == 'cancel':
        user.curr_input = None
        Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
        Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)

        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
        except:
            pass

        reply_text = TGText.objects.get(slug='welcome', language=user.language).text

        bot.send_message(chat_id=chat_id,
                            text=reply_text,
                            reply_markup=keyboards.flight_or_parcel_keyboard(user.language),
                            parse_mode='Markdown',
                            )


@bot.message_handler(content_types=['photo'])
def handle_contact(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    photo = message.photo[-1].file_id

    user = TGUser.objects.get(user_id=user_id)
    if username:
        user.username = username
        user.save()

    user_language = user.language
    curr_input = user.curr_input

    if curr_input and curr_input == 'passport':
        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()
        if (flight and parcel) or (not flight and not parcel):
            Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
            Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)
            user.curr_input = None
            user.save()

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=user_id,
                            text=error,
                            parse_mode='Markdown',
                            )

        else:
            counter = 0
            try:
                file_info = bot.get_file(photo)
                downloaded_file = bot.download_file(file_info.file_path)
                
                photo_info = functions.parse_passport(downloaded_file)
            except:
                counter = config.PARSE_COUNT
                photo_info = [None, None, None, None, None, None, None]


            for info in photo_info:
                if info:
                    counter += 1

            if counter >= config.PARSE_COUNT:
                folder, _ = Folder.objects.get_or_create(name="Паспорта")

                if flight:
                    slug = 'flight'
                elif parcel:
                    slug = 'parcel'

                try:
                    passport = Image(
                        folder=folder,
                        original_filename=f"{slug}_{flight.pk}.{file_info.file_path.split('.')[-1]}",
                    )
                    passport.file.save(passport.original_filename, ContentFile(downloaded_file))
                    passport.save()
                except:
                    pass

                name, family_name, passport_number, sex, birth_date, start_date, end_date = photo_info

                if flight:
                    flight.passport_photo_flight = passport
                    flight.name = utils.escape_markdown(name)
                    flight.family_name = utils.escape_markdown(family_name)
                    flight.passport_number = passport_number
                    flight.sex = sex
                    flight.birth_date = birth_date
                    flight.start_date = start_date
                    flight.end_date = end_date
                    flight.passport_photo_id = photo
                    flight.save()

                elif parcel:
                    parcel.passport_photo_parcel = passport
                    parcel.name = utils.escape_markdown(name)
                    parcel.family_name = utils.escape_markdown(family_name)
                    parcel.passport_number = passport_number
                    parcel.sex = sex
                    parcel.birth_date = birth_date
                    parcel.start_date = start_date
                    parcel.end_date = end_date
                    parcel.passport_photo_id = photo
                    parcel.save()
                
                user.curr_input = 'name'
                user.save()

                if name:
                    name_confirm = TGText.objects.get(slug='name_correct_question', language=user_language).text
                    reply_text = f'{name_confirm} *{name}*?'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                            parse_mode='Markdown',
                            )

                else:
                    name_question = TGText.objects.get(slug='name_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=name_question,
                            parse_mode='Markdown',
                            )

            else:
                wrong_passport = TGText.objects.get(slug='wrong_passport', language=user_language).text
                bot.send_message(chat_id=user_id,
                                text=wrong_passport,
                                parse_mode='Markdown',
                                )


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    phone = message.contact.phone_number
    user_id = str(message.from_user.id)
    username = message.from_user.username
    chat_id = message.chat.id

    user = TGUser.objects.get(user_id=user_id)
    if username:
        user.username = username
        user.save()

    user_language = user.language
    curr_input = user.curr_input

    if curr_input and curr_input == 'phone':
        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()
        if (flight and parcel) or (not flight and not parcel):
            Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
            Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)
            user.curr_input = None
            user.save()

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=user_id,
                            text=error,
                            reply_markup=telebot.types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            )
        else:
            user.curr_input = 'address'
            user.save()

            if flight:
                flight.phone = phone
                flight.save()
            elif parcel:
                parcel.phone = phone
                parcel.save()

            question = TGText.objects.get(slug='address_question', language=user_language).text
            bot.send_message(chat_id=chat_id,
                            text=question,
                            reply_markup=telebot.types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            disable_notification=True,
                            )


@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Handles message with type text."""

    user_id = str(message.from_user.id)
    username = message.from_user.username
    chat_id = message.chat.id

    user = TGUser.objects.get(user_id=user_id)
    if username:
        user.username = username
        user.save()

    user_language = user.language
    curr_input = user.curr_input
    input_info = utils.escape_markdown(message.text)

    if curr_input:
        flight = Flight.objects.filter(user=user, complete__isnull=True).first()
        parcel = Parcel.objects.filter(user=user, complete__isnull=True).first()
        if (flight and parcel) or (not flight and not parcel):
            Flight.objects.filter(user=user, complete__isnull=True).update(complete=False)
            Parcel.objects.filter(user=user, complete__isnull=True).update(complete=False)
            user.curr_input = None
            user.save()

            error = TGText.objects.get(slug='error', language=user_language).text
            bot.send_message(chat_id=user_id,
                            text=error,
                            reply_markup=telebot.types.ReplyKeyboardRemove(),
                            parse_mode='Markdown',
                            )
        else:
            if curr_input == 'name':
                if flight:
                    flight.name = input_info
                    flight.save()
                    family_name = flight.family_name
                elif parcel:
                    parcel.name = input_info
                    parcel.save()
                    family_name = parcel.family_name
                
                user.curr_input = 'familyname'
                user.save()

                if family_name:
                    confirm_text = TGText.objects.get(slug='familyname_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{family_name}*?'

                    bot.send_message(chat_id=chat_id,
                                    text=reply_text,
                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                    parse_mode='Markdown',
                                    )

                else:
                    question = TGText.objects.get(slug='familyname_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'familyname':
                if flight:
                    flight.family_name = input_info
                    flight.save()
                    passport_num = flight.passport_number
                elif parcel:
                    parcel.family_name = input_info
                    parcel.save()
                    passport_num = parcel.passport_number
                
                user.curr_input = 'passportnum'
                user.save()

                if passport_num:
                    confirm_text = TGText.objects.get(slug='passport_correct_question', language=user_language).text
                    reply_text = f'{confirm_text} *{passport_num}*?'

                    bot.send_message(chat_id=chat_id,
                                    text=reply_text,
                                    reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                    parse_mode='Markdown',
                                    )

                else:
                    question = TGText.objects.get(slug='passport_question', language=user_language).text

                    bot.send_message(chat_id=user_id,
                            text=question,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'passportnum':
                passport_num = utils.validate_passport(input_info)
                if passport_num:
                    if flight:
                        flight.passport_number = passport_num
                        flight.save()
                        sex = flight.sex
                    elif parcel:
                        parcel.passport_number = passport_num
                        parcel.save()
                        sex = parcel.sex
                    
                    user.curr_input = 'sex'
                    user.save()

                    if sex:
                        confirm_text = TGText.objects.get(slug='sex_correct_question', language=user_language).text
                        reply_text = f'{confirm_text} *{sex}*?'

                        bot.send_message(chat_id=chat_id,
                                            text=reply_text,
                                            reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                            parse_mode='Markdown',
                                            )

                    else:
                        question = TGText.objects.get(slug='sex_question', language=user_language).text

                        bot.send_message(chat_id=user_id,
                                text=question,
                                reply_markup=keyboards.sex_keyboard(user_language),
                                parse_mode='Markdown',
                                )

                else:
                    error = TGText.objects.get(slug='not_valid', language=user_language).text
                    question = TGText.objects.get(slug='passport_question', language=user_language).text
                    reply_text = f'{error}\n{question}'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'birthdate':
                birth_date = utils.validate_date(input_info)
                if birth_date:
                    if flight:
                        flight.birth_date = birth_date
                        flight.save()
                        start_date = flight.start_date
                    elif parcel:
                        parcel.birth_date = birth_date
                        parcel.save()
                        start_date = parcel.start_date
                    
                    user.curr_input = 'satrtdate'
                    user.save()

                    if start_date:
                        start_date = start_date.strftime('%d.%m.%Y')

                        confirm_text = TGText.objects.get(slug='start_correct_question', language=user_language).text
                        reply_text = f'{confirm_text} *{start_date}*?'

                        bot.send_message(chat_id=chat_id,
                                            text=reply_text,
                                            reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                            parse_mode='Markdown',
                                            )

                    else:
                        question = TGText.objects.get(slug='start_question', language=user_language).text

                        bot.send_message(chat_id=user_id,
                                text=question,
                                parse_mode='Markdown',
                                )

                else:
                    error = TGText.objects.get(slug='not_valid', language=user_language).text
                    question = TGText.objects.get(slug='birth_question', language=user_language).text
                    reply_text = f'{error}\n{question}'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'startdate':
                start_date = utils.validate_date(input_info)
                if start_date:
                    if flight:
                        flight.start_date = start_date
                        flight.save()
                        end_date = flight.end_date
                    elif parcel:
                        parcel.start_date = start_date
                        parcel.save()
                        end_date = parcel.end_date
                    
                    user.curr_input = 'enddate'
                    user.save()

                    if end_date:
                        end_date = end_date.strftime('%d.%m.%Y')

                        confirm_text = TGText.objects.get(slug='end_correct_question', language=user_language).text
                        reply_text = f'{confirm_text} *{start_date}*?'

                        bot.send_message(chat_id=chat_id,
                                            text=reply_text,
                                            reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                                            parse_mode='Markdown',
                                            )

                    else:
                        question = TGText.objects.get(slug='end_question', language=user_language).text

                        bot.send_message(chat_id=user_id,
                                text=question,
                                parse_mode='Markdown',
                                )
                
                else:
                    error = TGText.objects.get(slug='not_valid', language=user_language).text
                    question = TGText.objects.get(slug='start_question', language=user_language).text
                    reply_text = f'{error}\n{question}'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'enddate':
                end_date = utils.validate_date(input_info)
                if end_date:
                    if flight:
                        flight.end_date = end_date
                        flight.save()
                    elif parcel:
                        parcel.end_date = end_date
                        parcel.save()
                    
                    user.curr_input = 'phone'
                    user.save()

                    phone_question = TGText.objects.get(slug='phone_question', language=user_language).text
                    bot.send_message(chat_id=chat_id,
                            text=phone_question,
                            parse_mode='Markdown',
                            reply_markup=keyboards.request_phone_keyboard(user_language),
                            )

                else:
                    error = TGText.objects.get(slug='not_valid', language=user_language).text
                    question = TGText.objects.get(slug='end_question', language=user_language).text
                    reply_text = f'{error}\n{question}'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'phone':
                phone = utils.validate_phone(input_info)
                if phone:
                    if flight:
                        flight.phone = phone
                        flight.save()
                    elif parcel:
                        parcel.phone = phone
                        parcel.save()

                    user.curr_input = 'address'
                    user.save()

                    question = TGText.objects.get(slug='address_question', language=user_language).text
                    bot.send_message(chat_id=chat_id,
                            text=question,
                            parse_mode='Markdown',
                            )
                
                else:
                    error = TGText.objects.get(slug='not_valid', language=user_language).text
                    question = TGText.objects.get(slug='phone_question', language=user_language).text
                    reply_text = f'{error}\n{question}'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )

            elif curr_input == 'address':
                confirm_application = TGText.objects.get(slug='confirm_application', language=user_language).text
                name = TGText.objects.get(slug='name', language=user_language).text
                family_name = TGText.objects.get(slug='familyname', language=user_language).text
                passport = TGText.objects.get(slug='passport', language=user_language).text
                sex = TGText.objects.get(slug='sex', language=user_language).text
                birth_date = TGText.objects.get(slug='birth', language=user_language).text
                start_date = TGText.objects.get(slug='start', language=user_language).text
                end_date = TGText.objects.get(slug='end', language=user_language).text
                phone = TGText.objects.get(slug='phone', language=user_language).text
                address = TGText.objects.get(slug='address', language=user_language).text
                
                if flight:
                    route = TGText.objects.get(slug='route', language=user_language).text
                    flight_type = TGText.objects.get(slug='type_flight', language=user_language).text
                    departure_date = TGText.objects.get(slug='departure', language=user_language).text
                    arrival_date = TGText.objects.get(slug='arrival', language=user_language).text

                    flight.address = input_info
                    flight.save()

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = TGText.objects.get(slug='oneway_button', language=user_language).text.lower()
                    else:
                        flight_type_text = TGText.objects.get(slug='roundtrip_button', language=user_language).text.lower()

                    reply_text = f'{confirm_application}\n'
                    reply_text += f'\n*{route}* {flight.route.route}'
                    reply_text += f'\n*{flight_type}* {flight_type_text}'
                    reply_text += f'\n*{departure_date}* {flight.departure_date}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date}* {flight.arrival_date}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name}* {flight.name}'
                    reply_text += f'\n*{family_name}* {flight.family_name}'
                    reply_text += f'\n*{passport}* {flight.passport_number}'
                    reply_text += f'\n*{sex}* {flight.sex}'
                    reply_text += f'\n*{birth_date}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone}* {flight.phone}'
                    reply_text += f'\n*{address}* {flight.address}'


                elif parcel:
                    parcel_type = TGText.objects.get(slug='type_parcel', language=user_language).text
                    items_list = TGText.objects.get(slug='contains', language=user_language).text
                    fio_receiver = TGText.objects.get(slug='fio_receiver', language=user_language).text
                    phone_receiver = TGText.objects.get(slug='receiver_phone', language=user_language).text

                    parcel.address = input_info
                    parcel.save()

                    photo_id = parcel.passport_photo_id

                    reply_text = f'{confirm_application}\n'
                    reply_text += f'\n*{parcel_type}* {parcel.variation.name}'
                    reply_text += f'\n*{items_list}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name}* {parcel.name}'
                    reply_text += f'\n*{family_name}* {parcel.family_name}'
                    reply_text += f'\n*{passport}* {parcel.passport_number}'
                    reply_text += f'\n*{sex}* {parcel.sex}'
                    reply_text += f'\n*{birth_date}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone}* {parcel.phone}'
                    reply_text += f'\n*{address}* {parcel.address}'

                user.curr_input = 'confirmation'
                user.save()

                bot.send_photo(chat_id=user_id,
                               caption=reply_text,
                               photo=photo_id,
                               reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                               parse_mode='Markdown',
                               disable_notification=False,
                               )
        
            elif parcel and curr_input == 'fio_receiver':
                parcel.fio_receiver = input_info
                parcel.save()

                user.curr_input = 'contains'
                user.save()

                question = TGText.objects.get(slug='contains_question', language=user_language).text
                bot.send_message(chat_id=chat_id,
                                text=question,
                                parse_mode='Markdown',
                                )
            
            elif parcel and curr_input == 'contains':
                parcel.items_list = input_info
                parcel.save()

                user.curr_input = 'phone_receiver'
                user.save()

                question = TGText.objects.get(slug='phone_receiver_question', language=user_language).text
                bot.send_message(chat_id=chat_id,
                                text=question,
                                parse_mode='Markdown',
                                )

            elif parcel and curr_input == 'phone_receiver':
                phone_receiver = utils.validate_phone(input_info)
                if phone_receiver:
                    parcel.phone_receiver = phone_receiver
                    parcel.save()

                    user.curr_input = 'passport'
                    user.save()

                    if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
                    user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                        reuse = TGText.objects.get(slug='reuse', language=user_language).text
                        name = TGText.objects.get(slug='name', language=user_language).text
                        family_name = TGText.objects.get(slug='familyname', language=user_language).text
                        passport = TGText.objects.get(slug='passport', language=user_language).text
                        sex = TGText.objects.get(slug='sex', language=user_language).text
                        birth_date = TGText.objects.get(slug='birth', language=user_language).text
                        start_date = TGText.objects.get(slug='start', language=user_language).text
                        end_date = TGText.objects.get(slug='end', language=user_language).text
                        phone = TGText.objects.get(slug='phone', language=user_language).text
                        address = TGText.objects.get(slug='address', language=user_language).text

                        photo_id = user.passport_photo_id

                        reply_text = f'{reuse}\n'
                        
                        reply_text += f'\n*{name}* {user.name}'
                        reply_text += f'\n*{family_name}* {user.family_name}'
                        reply_text += f'\n*{passport}* {user.passport_number}'
                        reply_text += f'\n*{sex}* {user.sex}'
                        reply_text += f'\n*{birth_date}* {user.birth_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{start_date}* {user.start_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{end_date}* {user.end_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{phone}* {user.phone}'
                        reply_text += f'\n*{address}* {user.addresses}'

                        bot.send_photo(chat_id=user_id,
                               caption=reply_text,
                               photo=photo_id,
                               reply_markup=keyboards.confirm_or_hand_write_keyboard(user.curr_input, user_language),
                               parse_mode='Markdown',
                               disable_notification=False,
                               )

                    else:
                        passport_request = TGText.objects.get(slug='passport_photo_question', language=user_language).text

                        bot.send_message(chat_id=user_id,
                                text=passport_request,
                                parse_mode='Markdown',
                                )

                else:
                    error = TGText.objects.get(slug='not_valid', language=user_language).text
                    question = TGText.objects.get(slug='phone_receiver_question', language=user_language).text
                    reply_text = f'{error}\n{question}'

                    bot.send_message(chat_id=user_id,
                            text=reply_text,
                            parse_mode='Markdown',
                            )


if __name__ == '__main__':
    bot.polling(timeout=80)
    # while True:
    #     try:
    #         bot.polling()
    #     except:
    #         pass