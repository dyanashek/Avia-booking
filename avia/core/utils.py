import requests
import datetime
import aiohttp
import ssl
import certifi

from asgiref.sync import sync_to_async

from django.conf import settings
from django.http import HttpResponse

from config import TELEGRAM_TOKEN


async def send_pickup_address(application, application_type):
    if application_type == 'flight':
        order_id = '1'
        route = await sync_to_async(lambda: application.route)()
        departure_date = application.departure_date.strftime('%d.%m.%Y')
        notes = f'Билет {application.type} {route.route}, {departure_date}'
    elif application_type == 'parcel':
        order_id = '2'
        variation = await sync_to_async(lambda: application.variation)()
        notes = f'Посылка, {variation.name}: {application.items_list}'

    data = {
        'address': {
            'addressLineOne': application.address,
            'country': 'Israel',
        },
        'recipient': {
            'name': f'{application.name} {application.family_name}',
            'phone': application.phone,
        },
        'orderInfo': {
            'products': [f'{application.price} ₪'],
            'sellerOrderId': order_id,
        },
        'activity': 'pickup',
        'notes': notes,
    }

    async with aiohttp.ClientSession() as session:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())
            async with session.post(settings.ADD_STOP_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data, ssl=ssl_context) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        stop_id = response_data.get('id')
                    else:
                        stop_id = False
        except Exception as ex:
            stop_id = False

    return stop_id


async def send_sim_delivery_address(phone, user, fare):
    notes = f'Симка, {fare.title}, {phone}, за тариф(первый месяц) + подключение: {fare.price + 50} ₪'

    data = {
        'address': {
            'addressLineOne': user.addresses,
            'country': 'Israel',
        },
        'recipient': {
            'name': f'{user.name} {user.family_name}',
            'phone': phone,
        },
        'orderInfo': {
            'products': [fare.title],
            'sellerOrderId': '4',
        },
        'activity': 'delivery',
        'notes': notes,
    }

    async with aiohttp.ClientSession() as session:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())
            async with session.post(settings.ADD_STOP_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data, ssl=ssl_context) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        stop_id = response_data.get('id')
                    else:
                        stop_id = False
        except Exception as ex:
            stop_id = False

    return stop_id


async def send_sim_money_collect_address(phone, user, debt):
    notes = f'Симка - сбор денег, {phone}, {debt} ₪'

    data = {
        'address': {
            'addressLineOne': user.addresses,
            'country': 'Israel',
        },
        'recipient': {
            'name': f'{user.name} {user.family_name}',
            'phone': phone,
        },
        'orderInfo': {
            'sellerOrderId': '5',
        },
        'activity': 'pickup',
        'notes': notes,
    }

    async with aiohttp.ClientSession() as session:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())
            async with session.post(settings.ADD_STOP_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data, ssl=ssl_context) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        stop_id = response_data.get('id')
                    else:
                        stop_id = False
        except Exception as ex:
            stop_id = False

    return stop_id


def send_message_on_telegram(params, token=TELEGRAM_TOKEN):
    """Отправка сообщения в телеграм."""
    endpoint = f'https://api.telegram.org/bot{token}/sendMessage'
    response = requests.post(endpoint, params=params)
    return HttpResponse()