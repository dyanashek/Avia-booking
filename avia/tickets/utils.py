import requests
import tempfile

import pandas

from errors.models import AppError
from django.conf import settings


def reoptimize_plan():
    data = {
        'optimizationType': 'reorder_changed_stops',
    }

    requests.post(settings.REOPTIMIZE_PLAN_ENDPOINT, headers=settings.CURCUIT_HEADER, json=data)


def redistribute_plan():
    requests.post(settings.REDISTRIBUTE_PLAN_ENDPOINT , headers=settings.CURCUIT_HEADER)


def send_ticket_pickup_address(application):
    order_id = '6'
    route = application.route
    departure_date = str(application.departure_date)
    notes = f'Билет {application.type} {route.route}, {departure_date}'
    activity = 'delivery'

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
    except Exception as ex:
        stop_id = False
        response = None

        try:
            AppError.objects.create(
                source='5',
                error_type='3',
                main_user=application.user.user_id,
                description=f'Не удалось создать остановку в circuit (покупка билета). {application.id}. {ex}',
            )
        except:
            pass
    
    if response is not None:
        if response.status_code == 200:
            stop_id = response.json().get('stop').get('id')
            try:
                reoptimize_plan()
                redistribute_plan()
            except Exception as ex:
                try:
                    AppError.objects.create(
                        source='5',
                        error_type='3',
                        main_user=application.user.user_id,
                        description=f'Не удалось оптимизировать план в circuit (покупка билета). {application.id}. {ex}',
                    )
                except:
                    pass

        else:
            stop_id = False

            try:
                error_info = response.json()
            except:
                error_info = ''
            try:
                AppError.objects.create(
                    source='5',
                    error_type='3',
                    main_user=application.user.user_id,
                    description=f'Не удалось создать остановку в circuit (покупка билета). {application.id}. {response.status_code}, {error_info}',
                )
            except:
                pass

    else:
        stop_id = False

    return stop_id


def create_excel_file(data, date_from, date_to):
    data_frame = pandas.DataFrame(list(data))
    data_frame.columns = ['Менеджер', 
                          'Кол-во билетов', 
                          'Суммарная стоимость билетов',
                          ]

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        date_from = date_from.strftime('%d.%m.%Y')
        date_to = date_to.strftime('%d.%m.%Y')
        data_frame.to_excel(temp_file.name, index=False, sheet_name=f'{date_from} - {date_to}')
        
        return temp_file.name
        