import requests
import tempfile

import pandas

from django.conf import settings

def reoptimize_plan():
    data = {
        'optimizationType': 'reorder_changed_stops',
    }

    requests.post(settings.REOPTIMIZE_PLAN_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data)


def redistribute_plan():
    requests.post(settings.REDISTRIBUTE_PLAN_ENDPOINT , headers=settings.CURCUIT_HEADER)


def send_parcel_pickup_address(application):
    order_id = '7'
    variation = application.variation
    notes = f'Посылка, {variation.name}: {application.items_list}'
    activity = 'pickup'

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


def create_excel_file(data, date_from, date_to):
    data_frame = pandas.DataFrame(list(data))
    data_frame.columns = ['Менеджер', 
                          'Кол-во посылок', 
                          'Суммарная стоимость посылок',
                          ]

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        date_from = date_from.strftime('%d.%m.%Y')
        date_to = date_to.strftime('%d.%m.%Y')
        data_frame.to_excel(temp_file.name, index=False, sheet_name=f'{date_from} - {date_to}')
        
        return temp_file.name