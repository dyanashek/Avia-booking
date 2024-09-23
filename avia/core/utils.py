import requests
import aiohttp
import ssl
import certifi
import tempfile


import pandas

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
        activity = 'delivery'
    elif application_type == 'parcel':
        order_id = '2'
        variation = await sync_to_async(lambda: application.variation)()
        notes = f'Посылка, {variation.name}: {application.items_list}'
        activity = 'pickup'

    if not application.lat or not application.lon:
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
            'activity': activity,
            'notes': notes,
        }
    else:
        data = {
            'address': {
                'latitude': application.lat,
                'longitude': application.lon,
            },
            'recipient': {
                'name': f'{application.name} {application.family_name}',
                'phone': application.phone,
            },
            'orderInfo': {
                'products': [f'{application.price} ₪'],
                'sellerOrderId': order_id,
            },
            'activity': activity,
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

    if not user.lat or not user.lon:
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
    else:
        data = {
            'address': {
                'latitude': user.lat,
                'longitude': user.lon,
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

    if not user.lat or not user.lon:
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
            'activity': 'delivery',
            'notes': notes,
        }
    else:
        data = {
            'address': {
                'latitude': user.lat,
                'longitude': user.lon,
            },
            'recipient': {
                'name': f'{user.name} {user.family_name}',
                'phone': phone,
            },
            'orderInfo': {
                'sellerOrderId': '5',
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


async def get_address(lat, lon):
    async with aiohttp.ClientSession() as session:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())
            async with session.get(f'https://geocode-maps.yandex.ru/1.x/?apikey={settings.GEOCODE_KEY}&geocode={lon},{lat}&format=json', ssl=ssl_context) as response:
                response_data = await response.json()
                address = response_data.get('response').get('GeoObjectCollection').get('featureMember')[0].get('GeoObject').get('metaDataProperty').get('GeocoderMetaData').get('Address').get('formatted')
        except:
            address = 'Israel'

    return address


def send_message_on_telegram(params, token=TELEGRAM_TOKEN):
    """Отправка сообщения в телеграм."""
    endpoint = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        response = requests.post(endpoint, params=params)
    except:
        response = None
    return response


def send_improved_message_on_telegram(params, files=False, token=TELEGRAM_TOKEN):
    """Отправка сообщения в телеграм."""
    if files:
        try:
            endpoint = f'https://api.telegram.org/bot{token}/sendPhoto'
            response = requests.post(endpoint, data=params, files=files)
        except:
            response = False
    else:
        try:
            endpoint = f'https://api.telegram.org/bot{token}/sendMessage'
            response = requests.post(endpoint, data=params)
        except:
            response = False

    return response


def send_pickup_address_sync(application, application_type):
    if application_type == 'flight':
        order_id = '1'
        route = application.route
        departure_date = application.departure_date.strftime('%d.%m.%Y')
        notes = f'Билет {application.type} {route.route}, {departure_date}'
        activity = 'delivery'
    elif application_type == 'parcel':
        order_id = '2'
        variation = application.variation
        notes = f'Посылка, {variation.name}: {application.items_list}'
        activity = 'pickup'

    if not application.lat or not application.lon:
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
            'activity': activity,
            'notes': notes,
        }
    else:
        data = {
            'address': {
                'latitude': application.lat,
                'longitude': application.lon,
            },
            'recipient': {
                'name': f'{application.name} {application.family_name}',
                'phone': application.phone,
            },
            'orderInfo': {
                'products': [f'{application.price} ₪'],
                'sellerOrderId': order_id,
            },
            'activity': activity,
            'notes': notes,
        }

    try:
        response = requests.post(settings.ADD_STOP_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data)
    except:
        stop_id = False
        response = None
    
    if response:
        if response.status_code == 200:
            stop_id = response.json().get('stop').get('id')
            try:
                reoptimize_plan()
                redistribute_plan()
            except:
                pass
        else:
            stop_id = False
    else:
        stop_id = False

    return stop_id


def send_sim_delivery_address_sync(phone, user, fare):
    notes = f'Симка, {fare.title}, {phone}, за тариф(первый месяц) + подключение: {fare.price + 50} ₪'

    if not user.lat or user.lon:
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
    else:
        data = {
            'address': {
                'latitude': user.lat,
                'longitude': user.lon,
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

    try:
        response = requests.post(settings.ADD_STOP_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data)
    except:
        stop_id = False
        response = None
    
    if response:
        if response.status_code == 200:
            stop_id = response.json().get('stop').get('id')
            try:
                reoptimize_plan()
                redistribute_plan()
            except:
                pass
        else:
            stop_id = False
    else:
        stop_id = False


    return stop_id


def create_icount_client_sync(user, phone):
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

    try:
        response = requests.post(ICOUNT_CREATE_USER_ENDPOINT, data=data)
    except:
        icount_client_id = False
        response = None

    if response:
        try:
            icount_client_id = response.json().get('client_id')
        except:
            icount_client_id = False
    else:
        icount_client_id = False

    return icount_client_id


def send_sim_money_collect_address_sync(phone, user, debt):
    notes = f'Симка - сбор денег, {phone}, {debt} ₪'

    if not user.lat or not user.lon:
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
            'activity': 'delivery',
            'notes': notes,
        }
    else:
        data = {
            'address': {
                'latitude': user.lat,
                'longitude': user.lon,
            },
            'recipient': {
                'name': f'{user.name} {user.family_name}',
                'phone': phone,
            },
            'orderInfo': {
                'sellerOrderId': '5',
            },
            'activity': 'delivery',
            'notes': notes,
        }

    try:
        response = requests.post(settings.ADD_STOP_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data)
    except:
        stop_id = False
        response = None
    
    if response:
        if response.status_code == 200:
            stop_id = response.json().get('stop').get('id')
            try:
                reoptimize_plan()
                redistribute_plan()
            except:
                pass
        else:
            stop_id = False
    else:
        stop_id = False

    return stop_id


def create_icount_invoice_sync(user_id, amount, is_old_sim=False):
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

    try:
        response = requests.post(ICOUNT_CREATE_INVOICE_ENDPOINT, json=data)
    except:
        doc_url = False
        response = None
    
    if response:
        try:
            doc_url = response.json().get('doc_url')
        except:
            doc_url = False
    else:
        doc_url = False

    return doc_url


def create_excel_file(data, old=True):
    data_frame = pandas.DataFrame(list(data))
    data_frame.columns = ['Номер', 
                          'Долг',]

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        if old:
            data_frame.to_excel(temp_file.name, index=False, sheet_name=f'Старые сим карты')
        else:
            data_frame.to_excel(temp_file.name, index=False, sheet_name=f'Cим карты')

        return temp_file.name
        