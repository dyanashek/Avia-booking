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

from core.models import TGText, Language, Route, ParcelVariation, SimFare

#* <------------------------------------------------->
#! КЛАВИАТУРЫ ДЛЯ БОТА КЛИЕНТОВ (АВИА, ПОСЫЛКИ, СИМКИ)
#* <------------------------------------------------->

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
    sim_button = await sync_to_async(TGText.objects.get)(slug='sim_button', language=language)

    # keyboard.add(types.InlineKeyboardButton(text=flight_button.text, callback_data = f'flight'))
    # keyboard.add(types.InlineKeyboardButton(text=parcel_button.text, callback_data = f'parcel'))
    transfer = types.InlineKeyboardButton(text='Перевод', url = 'https://t.me/Roma0927')
    keyboard.row(types.InlineKeyboardButton(text=sim_button.text, callback_data = f'sim'), transfer)

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

    back_button = await sync_to_async(TGText.objects.get)(slug='back_button', language=language)
    keyboard.row(types.InlineKeyboardButton(text=back_button.text, callback_data=f'curryear_{direction}'))

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


async def ready_pay_keyboard(language):
    keyboard = InlineKeyboardBuilder()

    ready_pay_button = await sync_to_async(TGText.objects.get)(slug='ready_pay_button', language=language)
    week_later_button = await sync_to_async(TGText.objects.get)(slug='later_week_button', language=language)
    month_later_button = await sync_to_async(TGText.objects.get)(slug='later_month_button', language=language)

    keyboard.row(types.InlineKeyboardButton(text=ready_pay_button.text, callback_data='readypay'))
    keyboard.row(types.InlineKeyboardButton(text=week_later_button.text, callback_data='later_week'))
    keyboard.row(types.InlineKeyboardButton(text=month_later_button.text, callback_data='later_month'))

    return keyboard.as_markup()


#* <------------------------------------------------->
#! КЛАВИАТУРЫ ДЛЯ СИМОК
#* <------------------------------------------------->

async def sim_fares_keyboard():
    keyboard = InlineKeyboardBuilder()

    fares = await sync_to_async(SimFare.objects.all)()
    async for fare in fares:
        keyboard.row(types.InlineKeyboardButton(text=fare.title, callback_data = f'fare_{fare.pk}'))

    return keyboard.as_markup()


async def sim_confirm_or_hand_write_keyboard(input_info, language):
    keyboard = InlineKeyboardBuilder()

    confirm_button = await sync_to_async(TGText.objects.get)(slug='confirm_button', language=language)
    keyboard.row(types.InlineKeyboardButton(text=confirm_button.text, callback_data=f's-confirm_{input_info}'))

    handwrite_button = await sync_to_async(TGText.objects.get)(slug='hand_write_button', language=language)
    keyboard.row(types.InlineKeyboardButton(text=handwrite_button.text, callback_data=f's-hand_{input_info}'))

    return keyboard.as_markup()


async def sim_confirmation_keyboard(fare_id, language):
    keyboard = InlineKeyboardBuilder()

    confirm_button = await sync_to_async(TGText.objects.get)(slug='confirm_button', language=language)
    keyboard.row(types.InlineKeyboardButton(text=confirm_button.text, callback_data=f's-confirm_fare_{fare_id}'))
    
    cancel_button = await sync_to_async(TGText.objects.get)(slug='cancel_button', language=language)
    keyboard.row(types.InlineKeyboardButton(text=cancel_button.text, callback_data='s-cancel'))

    back_button = await sync_to_async(TGText.objects.get)(slug='back_button', language=language)
    keyboard.row(types.InlineKeyboardButton(text=back_button.text, callback_data='back_fares'))

    return keyboard.as_markup()


async def sim_confirm_application_keyboard(user_id, fare_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Подтвердить', callback_data=f'm-sim_{user_id}_{fare_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Отклонить', callback_data=f's-refuse'))

    return keyboard.as_markup()


async def sim_confirm_phone_keyboard(user_id, fare_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Подтвердить', callback_data=f's-complete_{user_id}_{fare_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Ввести заново', callback_data=f's-retype_{user_id}_{fare_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Отклонить заявку', callback_data=f's-refuse'))

    return keyboard.as_markup()


#* <------------------------------------------------->
#! КЛАВИАТУРЫ ДЛЯ ВОДИТЕЛЕЙ (СИМКИ)
#* <------------------------------------------------->

async def confirm_amount_keyboard(amount, sim_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Подтвердить', callback_data=f'confirm_sim_{amount}_{sim_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Ввести заново', callback_data=f'retype_{sim_id}'))

    return keyboard.as_markup()


#* <------------------------------------------------->
#! КЛАВИАТУРЫ ДЛЯ ВЫДАЧИ ДЕНЕГ В САМАРКАНДЕ
#* <------------------------------------------------->

async def pass_money_keyboard(transfer_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Отметить выданным', callback_data=f'pass_{transfer_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Отменить', callback_data=f'cancel'))

    return keyboard.as_markup()


async def credit_money_keyboard(transfer_id):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Выдать в кредит', callback_data=f'credit_{transfer_id}'))
    keyboard.row(types.InlineKeyboardButton(text='Отменить', callback_data=f'cancel'))

    return keyboard.as_markup()

#* <------------------------------------------------->
#! КЛАВИАТУРЫ ДЛЯ ОТЧЕТОВ
#* <------------------------------------------------->
async def data_or_report_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Внести данные', callback_data=f'data_choose'))
    keyboard.row(types.InlineKeyboardButton(text='Отчет', callback_data=f'report_choose'))
    keyboard.row(types.InlineKeyboardButton(text='Последние записи', callback_data=f'db'))
    keyboard.row(types.InlineKeyboardButton(text='Отсутствующие курсы покупки', callback_data=f'missing'))

    return keyboard.as_markup()


async def data_type_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Все данные', callback_data=f'data_all'))
    keyboard.row(types.InlineKeyboardButton(text='Передано фирмам', callback_data=f'data_1'))
    keyboard.row(types.InlineKeyboardButton(text='Передано Равшану', callback_data=f'data_2'))
    keyboard.row(types.InlineKeyboardButton(text='Получено от фирм', callback_data=f'data_3'))
    keyboard.row(types.InlineKeyboardButton(text='Получено от Равшана', callback_data=f'data_4'))
    keyboard.row(types.InlineKeyboardButton(text='Курс покупки', callback_data=f'data_rate'))
    keyboard.row(types.InlineKeyboardButton(text='⬅️ Назад', callback_data=f'back_main'))

    return keyboard.as_markup()


async def report_type_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.row(types.InlineKeyboardButton(text='Текущие балансы', callback_data=f'report_balance'))
    keyboard.row(types.InlineKeyboardButton(text='За год', callback_data=f'report_year'))
    keyboard.row(types.InlineKeyboardButton(text='За месяц', callback_data=f'report_month'))
    keyboard.row(types.InlineKeyboardButton(text='За день', callback_data=f'report_day'))
    keyboard.row(types.InlineKeyboardButton(text='Выбрать период', callback_data=f'report_input'))
    keyboard.row(types.InlineKeyboardButton(text='⬅️ Назад', callback_data=f'back_main'))

    return keyboard.as_markup()


async def data_date_keyboard(data_type):
    keyboard = InlineKeyboardBuilder()

    curr_date = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    the_day_before_yesterday = (curr_date - datetime.timedelta(days=2)).date().strftime('%d.%m.%Y')
    yesterday = (curr_date - datetime.timedelta(days=1)).date().strftime('%d.%m.%Y')
    today = curr_date.date().strftime('%d.%m.%Y')

    keyboard.row(types.InlineKeyboardButton(text=the_day_before_yesterday, callback_data=f'date_{data_type}_{the_day_before_yesterday}'))
    keyboard.row(types.InlineKeyboardButton(text=yesterday, callback_data=f'date_{data_type}_{yesterday}'))
    keyboard.row(types.InlineKeyboardButton(text=today, callback_data=f'date_{data_type}_{today}'))
    keyboard.row(types.InlineKeyboardButton(text='Ввести вручную', callback_data=f'date_{data_type}_input'))
    keyboard.row(types.InlineKeyboardButton(text='⬅️ Назад', callback_data=f'back_data'))

    return keyboard.as_markup()
