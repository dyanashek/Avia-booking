import calendar
import datetime
import django
import os

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from django.db.models import Q

from core.models import TGText, Language, Route, ParcelVariation


async def choose_language_keyboard():
    keyboard = InlineKeyboardBuilder()
    languages = await sync_to_async(Language.objects.all)()

    async for language in languages:
        keyboard.row(types.InlineKeyboardButton(text=language.language, callback_data=f'language_{language.pk}'))

    return keyboard.as_markup()


async def flight_or_parcel_keyboard(language):
    keyboard = InlineKeyboardBuilder()

    flight_button = await sync_to_async(TGText.objects.get)(slug='flight_button', language=language)
    parcel_button = await sync_to_async(TGText.objects.get)(slug='parcel_button', language=language)

    keyboard.add(types.InlineKeyboardButton(text=flight_button.text, callback_data = f'flight'))
    keyboard.add(types.InlineKeyboardButton(text=parcel_button.text, callback_data = f'parcel'))

    return keyboard.as_markup()


async def route_keyboard():
    keyboard = InlineKeyboardBuilder()

    routes = await sync_to_async(Route.objects.all)()
    async for route in routes:
        keyboard.row(types.InlineKeyboardButton(text=route.route, callback_data = f'route_{route.pk}'))

    return keyboard.as_markup()


async def flight_type_keyboard(language):
    keyboard = InlineKeyboardBuilder()

    round = await sync_to_async(TGText.objects.get)(slug='roundtrip_button', language=language)
    oneway = await sync_to_async(TGText.objects.get)(slug='oneway_button', language=language)

    keyboard.add(types.InlineKeyboardButton(text=round.text, callback_data = f'flighttype_roundtrip'))
    keyboard.add(types.InlineKeyboardButton(text=oneway.text, callback_data = f'flighttype_oneway'))

    return keyboard.as_markup()


async def choose_month_keyboard(year, language, direction='departure'):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text=str(year), callback_data = f'nothing'))

    buttons = []
    months = await sync_to_async(lambda: list(TGText.objects.filter(Q(slug='month') & Q(language=language))))()

    for num, month in enumerate(months):
        if num + 1 >= datetime.date.today().month or year > datetime.date.today().year:
            buttons.append(types.InlineKeyboardButton(text=month.text, callback_data=f'month_{direction}_{year}_{num + 1}'))

        if (num + 1) % 3 == 0 or len(months) == num + 1:
            keyboard.row(*buttons)
            buttons = []


    if year == datetime.date.today().year:
        keyboard.row(types.InlineKeyboardButton(text='>>', callback_data = f'nextyear_{direction}'))
    else:
        keyboard.row(types.InlineKeyboardButton(text='<<', callback_data = f'curryear_{direction}'))

    return keyboard.as_markup()


async def choose_day_keyboard(days, language, direction='departure'):
    keyboard = InlineKeyboardBuilder()
    month = await sync_to_async(lambda: list(TGText.objects.filter(Q(slug='month') & Q(language=language))))()
    month = month[days[0].day.month - 1]
    keyboard.row(types.InlineKeyboardButton(text=month.text, callback_data=f'nothing'))

    buttons = []
    for num, day in enumerate(days):
        buttons.append(types.InlineKeyboardButton(text=str(day), callback_data=f'day_{direction}_{day.pk}'))
        if (num + 1) % 3 == 0 or len(days) == num + 1:
            keyboard.row(*buttons)
            buttons = []

    keyboard.row(types.InlineKeyboardButton(text='Назад', callback_data=f'curryear_{direction}'))

    return keyboard.as_markup()


async def confirm_or_hand_write_keyboard(input_info, language):
    keyboard = InlineKeyboardBuilder()

    confirm_button = await sync_to_async(TGText.objects.get)(slug='confirm_button', language=language)

    keyboard.row(types.InlineKeyboardButton(text=confirm_button.text, callback_data=f'confirm_{input_info}'))
    if input_info == 'confirmation':
        cancel_button = await sync_to_async(TGText.objects.get)(slug='cancel_button', language=language)
        keyboard.row(types.InlineKeyboardButton(text=cancel_button.text, callback_data=f'cancel'))
    else:
        handwrite_button = await sync_to_async(TGText.objects.get)(slug='hand_write_button', language=language)
        keyboard.row(types.InlineKeyboardButton(text=handwrite_button.text, callback_data=f'hand_{input_info}'))

    return keyboard.as_markup()


async def sex_keyboard(language):
    keyboard = InlineKeyboardBuilder()

    male_button = await sync_to_async(TGText.objects.get)(slug='male_button', language=language)
    female_button = await sync_to_async(TGText.objects.get)(slug='female_button', language=language)

    keyboard.add(types.InlineKeyboardButton(text=male_button.text, callback_data=f'sex_M'))
    keyboard.add(types.InlineKeyboardButton(text=female_button.text, callback_data=f'sex_F'))

    return keyboard.as_markup()


async def request_phone_keyboard(language):
    keyboard = ReplyKeyboardBuilder()
    button = await sync_to_async(TGText.objects.get)(slug='request_phone_button', language=language)
    keyboard.row(types.KeyboardButton(text=button.text, request_contact=True,))

    return keyboard.as_markup(resize_keyboard=True, one_time_keyboard=True,)


async def parcel_types_keyboard(language):
    keyboard = InlineKeyboardBuilder()
    variations = await sync_to_async(ParcelVariation.objects.filter(language=language).all)()

    async for variation in variations:
        keyboard.row(types.InlineKeyboardButton(text=variation.name, callback_data = f'parceltype_{variation.pk}'))

    return keyboard.as_markup()


async def confirm_application_keyboard(info_type, info_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Подтвердить', callback_data=f'price_{info_type}_{info_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Отклонить', callback_data=f'refuse_{info_type}_{info_id}'))

    return keyboard.as_markup()


async def confirm_price_keyboard(info_type, info_id, price):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Подтвердить', callback_data=f'complete_{info_type}_{info_id}_{price}'))
    keyboard.row(types.InlineKeyboardButton(text='Ввести заново', callback_data=f'price_{info_type}_{info_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Отклонить заявку', callback_data=f'refuse_{info_type}_{info_id}'))

    return keyboard.as_markup()