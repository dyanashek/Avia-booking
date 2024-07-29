import requests
import datetime
import aiohttp
import ssl
import certifi

from asgiref.sync import sync_to_async

from django.conf import settings
from django.http import HttpResponse

from config import (TELEGRAM_TOKEN, 
                    ICOUNT_COMPANY_ID, 
                    ICOUNT_USERNAME, 
                    ICOUNT_PASSWORD, 
                    OLD_ICOUNT_COMPANY_ID, 
                    OLD_ICOUNT_USERNAME, 
                    OLD_ICOUNT_PASSWORD, 
                    ICOUNT_CREATE_USER_ENDPOINT,
                    ICOUNT_CREATE_INVOICE_ENDPOINT,
                    )


def reoptimize_plan():
    data = {
        'optimizationType': 'reorder_changed_stops',
    }

    requests.post(settings.REOPTIMIZE_PLAN_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data)


def redistribute_plan():
    requests.post(settings.REDISTRIBUTE_PLAN_ENDPOINT , headers=settings.CURCUIT_HEADER)


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
                        stop_id = response_data.get('stop').get('id')

                        try:
                            reoptimize_plan()
                            redistribute_plan()
                        except:
                            pass
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
                        stop_id = response_data.get('stop').get('id')

                        try:
                            reoptimize_plan()
                            redistribute_plan()
                        except:
                            pass
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
                        stop_id = response_data.get('stop').get('id')

                        try:
                            reoptimize_plan()
                            redistribute_plan()
                        except:
                            pass
                    else:
                        response_data = await response.json()
                        stop_id = False
        except Exception as ex:
            stop_id = False

    return stop_id


async def create_icount_client(user, phone):
    cl_name = user.name
    if user.family_name:
        cl_name += f' {user.family_name}'
    data = {
        'cid': ICOUNT_COMPANY_ID,
        'user': ICOUNT_USERNAME,
        'pass': ICOUNT_PASSWORD,
        'client_name': cl_name,
        'first_name': user.name,
        'last_name': user.family_name,
        'mobile': phone
    }

    async with aiohttp.ClientSession() as session:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())
            async with session.post(ICOUNT_CREATE_USER_ENDPOINT, data=data, ssl=ssl_context) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        icount_client_id = response_data.get('client_id')
                    else:
                        icount_client_id = False
        except Exception as ex:
            icount_client_id = False

    return icount_client_id


async def create_icount_invoice(user_id, amount, is_old_sim=False):
    icount_cid = ICOUNT_COMPANY_ID
    icount_user = ICOUNT_USERNAME
    icount_pass = ICOUNT_PASSWORD
    if is_old_sim:
        icount_cid = OLD_ICOUNT_COMPANY_ID
        icount_user = OLD_ICOUNT_USERNAME
        icount_pass = OLD_ICOUNT_PASSWORD

    data = {
        'cid': icount_cid,
        'user': icount_user,
        'pass': icount_pass,
        'doctype': 'invrec',
        'client_id': user_id,
        'lang': 'en',
        'items': [
            {
                'description': 'Online support + simcard',
                'unitprice_incvat': float(amount),
                'quantity': 1,
            },
            ],
        'cash': {'sum': float(amount)},        
    }

    async with aiohttp.ClientSession() as session:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())
            async with session.post(ICOUNT_CREATE_INVOICE_ENDPOINT, json=data, ssl=ssl_context) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        doc_url = response_data.get('doc_url')
                    else:
                        doc_url = False
        except Exception as ex:
            doc_url = False

    return doc_url


def send_message_on_telegram(params, token=TELEGRAM_TOKEN):
    """Отправка сообщения в телеграм."""
    endpoint = f'https://api.telegram.org/bot{token}/sendMessage'
    response = requests.post(endpoint, params=params)
    return HttpResponse()