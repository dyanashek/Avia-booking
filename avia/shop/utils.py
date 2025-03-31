import requests
import time
import threading

from django.conf import settings

from errors.models import AppError
from config import ICOUNT_CREATE_USER_ENDPOINT


def format_amount(value):
    try:
        value = float(value)
    except:
        return 0
    
    return '{:,.2f}'.format(value).replace(',', ' ').rstrip('0').rstrip('.')


def escape_markdown(text: str) -> str:
    characters_to_escape = ['_', '*', '[', ']', '`']
    for char in characters_to_escape:
        text = text.replace(char, '\\' + char)

    return text


def create_icount_client(buyer, phone):
    data = {
        'cid': settings.SHOP_ICOUNT_COMPANY_ID,
        'user': settings.SHOP_ICOUNT_USERNAME,
        'pass': settings.SHOP_ICOUNT_PASSWORD,
        'client_name': buyer.user.first_name,
        'mobile': phone
    }

    try:
        response = requests.post(ICOUNT_CREATE_USER_ENDPOINT, data=data)
    except Exception as ex:
        error_info = str(ex)
        response = None

    if response and response.ok:
        try:
            icount_id = response.json().get('client_id')
            if icount_id:
                return icount_id
            
            try:
                error_info = response.json()
            except:
                error_info = ''

        except Exception as ex:
            try:
                error_info = response.json()
            except:
                error_info = ''

    try:
        AppError.objects.create(
            source='5',
            error_type='11',
            main_user=buyer.tg_id,
            description=f'Не удалось создать пользователя iCount (магазин) {phone}. {error_info}',
        )
    except:
        pass
    
    return False


def reoptimize_plan():
    data = {
        'optimizationType': 'reorder_changed_stops',
    }

    requests.post(f'{settings.CURCUIT_END_POINT}/plans/{settings.SHOP_CIRCUIT_PLAN}:reoptimize', headers=settings.CURCUIT_HEADER, json=data)


def redistribute_plan():
    response = requests.post(f'{settings.CURCUIT_END_POINT}/plans/{settings.SHOP_CIRCUIT_PLAN}:redistribute', headers=settings.CURCUIT_HEADER)
    start = time.time()
    while not response.ok:
        response = requests.post(f'{settings.CURCUIT_END_POINT}/plans/{settings.SHOP_CIRCUIT_PLAN}:redistribute', headers=settings.CURCUIT_HEADER)
        if time.time() - start > 60:
            break
        time.sleep(3)


def send_shop_delivery_address(order):
    error_info = ''
    notes = f'Заказ, #{order.id}:\n'
    for item in order.items.all():
        notes += f'\n{item.product.title} x {item.item_count}'

    data = {
        'address': {
            'addressLineOne': order.address,
            'country': 'Uzbekistan',
        },
        'recipient': {
            'name': order.user.first_name,
            'phone': order.phone,
        },
        'orderInfo': {
            'sellerOrderId': '8',
        },
        'activity': 'delivery',
        'notes': notes,
    }

    try:
        response = requests.post(f'{settings.CURCUIT_END_POINT}/plans/{settings.SHOP_CIRCUIT_PLAN}/stops:liveCreate', headers=settings.CURCUIT_HEADER, json=data)
    except Exception as ex:
        error_info = str(ex)
        response = None
    
    if response and response.ok:
        stop_id = response.json().get('stop').get('id')
        if stop_id:
            try:
                reoptimize_plan()
                threading.Thread(target=redistribute_plan).start()
            except Exception as ex:
                try:
                    AppError.objects.create(
                        source='5',
                        error_type='3',
                        main_user=order.user.username,
                        description=f'Не удалось оптимизировать план в circuit (магазин) {order.id}. {ex}',
                    )
                except:
                    pass

            return stop_id
        else:
            try:
                error_info = response.json()
            except:
                error_info = ''
    else:
        error_info = response.status_code

    try:
        AppError.objects.create(
            source='5',
            error_type='3',
            main_user=order.user.username,
            description=f'Не удалось создать остановку в circuit (магазин) {order.id}. {error_info}',
        )
    except:
        pass

    return False


def send_topup_address(topup):
    error_info = ''
    notes = f'Забор денег, #{topup.id}, {int(topup.amount)} '

    data = {
        'address': {
            'addressLineOne': topup.address,
            'country': 'Israel',
        },
        'recipient': {
            'name': topup.user.first_name,
            'phone': topup.phone,
        },
        'orderInfo': {
            'sellerOrderId': '9',
        },
        'activity': 'delivery',
        'notes': notes,
    }

    try:
        response = requests.post(f'{settings.CURCUIT_END_POINT}/plans/{settings.SHOP_TOPUP_CIRCUIT_PLAN}/stops:liveCreate', headers=settings.CURCUIT_HEADER, json=data)
    except Exception as ex:
        error_info = str(ex)
        response = None
    
    if response and response.ok:
        stop_id = response.json().get('stop').get('id')
        if stop_id:
            try:
                reoptimize_plan()
                threading.Thread(target=redistribute_plan).start()
            except Exception as ex:
                try:
                    AppError.objects.create(
                        source='5',
                        error_type='3',
                        main_user=topup.user.username,
                        description=f'Не удалось оптимизировать план в circuit (магазин - забор денег) {topup.id}. {ex}',
                    )
                except:
                    pass

            return stop_id
        else:
            try:
                error_info = response.json()
            except:
                error_info = ''
    else:
        error_info = response.status_code

    try:
        AppError.objects.create(
            source='5',
            error_type='3',
            main_user=topup.user.username,
            description=f'Не удалось создать остановку в circuit (магазин - забор денег) {topup.id}. {error_info}',
        )
    except:
        pass

    return False
