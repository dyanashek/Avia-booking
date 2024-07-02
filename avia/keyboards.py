import calendar
import datetime
import django
import os

from telebot import types

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from django.db.models import Q
from core.models import TGText, Language, Route, ParcelVariation


def choose_language_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    languages = Language.objects.all()

    for language in languages:
        keyboard.add(types.InlineKeyboardButton(language.language, callback_data = f'language_{language.pk}'))

    return keyboard


def flight_or_parcel_keyboard(language):
    keyboard = types.InlineKeyboardMarkup()

    flight_button = TGText.objects.get(slug='flight_button', language=language).text
    parcel_button = TGText.objects.get(slug='parcel_button', language=language).text

    keyboard.add(types.InlineKeyboardButton(flight_button, callback_data = f'flight'), types.InlineKeyboardButton(parcel_button, callback_data = f'parcel'))

    return keyboard


def route_keyboard():
    keyboard = types.InlineKeyboardMarkup()

    for route in Route.objects.all():
        keyboard.add(types.InlineKeyboardButton(route.route, callback_data = f'route_{route.pk}'))

    return keyboard


def flight_type_keyboard(language):
    keyboard = types.InlineKeyboardMarkup()

    round = TGText.objects.get(slug='roundtrip_button', language=language).text
    oneway = TGText.objects.get(slug='oneway_button', language=language).text

    keyboard.add(types.InlineKeyboardButton(round, callback_data = f'flighttype_roundtrip'), types.InlineKeyboardButton(oneway, callback_data = f'flighttype_oneway'))

    return keyboard


def choose_month_keyboard(year, language, direction='departure'):
    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(types.InlineKeyboardButton(year, callback_data = f'nothing'))

    months_buttons = []
    months = TGText.objects.filter(Q(slug='month') & Q(language=language)).all()
    for num, month in enumerate(months):
        if num + 1 >= datetime.date.today().month or year > datetime.date.today().year:
            months_buttons.append(types.InlineKeyboardButton(month.text, callback_data = f'month_{direction}_{year}_{num + 1}'))

        if (num + 1) % 3 == 0 or len(months) == num + 1:
            keyboard.add(*months_buttons)
            months_buttons = []

    if year == datetime.date.today().year:
        keyboard.add(types.InlineKeyboardButton('>>', callback_data = f'nextyear_{direction}'))
    else:
        keyboard.add(types.InlineKeyboardButton('<<', callback_data = f'curryear_{direction}'))

    return keyboard


def choose_day_keyboard(days, language, direction='departure'):
    keyboard = types.InlineKeyboardMarkup()
    month = TGText.objects.filter(Q(slug='month') & Q(language=language)).all()[days[0].day.month - 1]
    keyboard.add(types.InlineKeyboardButton(month.text, callback_data = f'nothing'))

    days_buttons = []
    for num, day in enumerate(days):
        days_buttons.append(types.InlineKeyboardButton(str(day), callback_data = f'day_{direction}_{day.pk}'))

        if (num + 1) % 3 == 0 or len(days) == num + 1:
            keyboard.add(*days_buttons)
            days_buttons = []

    keyboard.add(types.InlineKeyboardButton('Назад', callback_data = f'curryear_{direction}'))

    return keyboard


def confirm_or_hand_write_keyboard(input_info, language):
    keyboard = types.InlineKeyboardMarkup()

    confirm_button = TGText.objects.get(slug='confirm_button', language=language).text

    keyboard.add(types.InlineKeyboardButton(confirm_button, callback_data = f'confirm_{input_info}'))
    if input_info == 'confirmation':
        cancel_button = TGText.objects.get(slug='cancel_button', language=language).text
        keyboard.add(types.InlineKeyboardButton(cancel_button, callback_data = f'cancel'))
    else:
        handwrite_button = TGText.objects.get(slug='hand_write_button', language=language).text
        keyboard.add(types.InlineKeyboardButton(handwrite_button, callback_data = f'hand_{input_info}'))

    return keyboard


def sex_keyboard(language):
    keyboard = types.InlineKeyboardMarkup()

    male_button = TGText.objects.get(slug='male_button', language=language).text
    female_button = TGText.objects.get(slug='female_button', language=language).text

    keyboard.add(types.InlineKeyboardButton(male_button, callback_data = f'sex_M'))
    keyboard.add(types.InlineKeyboardButton(female_button, callback_data = f'sex_F'))

    return keyboard


def request_phone_keyboard(language):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True,)
    button = TGText.objects.get(slug='request_phone_button', language=language).text
    keyboard.add(types.KeyboardButton(button, request_contact=True,))

    return keyboard


def parcel_types_keyboard(language):
    keyboard = types.InlineKeyboardMarkup()
    
    for variation in ParcelVariation.objects.filter(language=language).all():
        keyboard.add(types.InlineKeyboardButton(variation.name, callback_data = f'parceltype_{variation.pk}'))

    return keyboard