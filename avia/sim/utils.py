import requests
import tempfile
import re

import pandas

from errors.models import AppError
from config import (OLD_ICOUNT_COMPANY_ID, 
                    OLD_ICOUNT_USERNAME, 
                    OLD_ICOUNT_PASSWORD,
                    ICOUNT_CREATE_USER_ENDPOINT,
                    )


def create_icount_client(name, phone):
    data = {
        'cid': OLD_ICOUNT_COMPANY_ID,
        'user': OLD_ICOUNT_USERNAME,
        'pass': OLD_ICOUNT_PASSWORD,
        'client_name': name,
        'first_name': name,
        'mobile': phone
    }

    try:
        response = requests.post(ICOUNT_CREATE_USER_ENDPOINT, data=data)
    except Exception as ex:
        icount_client_id = False
        response = None

        try:
            AppError.objects.create(
                source='5',
                error_type='4',
                description=f'Не удалось создать пользователя iCount {phone}. {ex}',
            )
        except:
            pass

    if response is not None:
        try:
            icount_client_id = response.json().get('client_id')
        except Exception as ex:
            icount_client_id = False

            try:
                AppError.objects.create(
                    source='5',
                    error_type='4',
                    description=f'Не удалось создать пользователя iCount {phone}. {ex}',
                )
            except:
                pass
    else:
        icount_client_id = False

    return icount_client_id


def create_excel_file(data, date_from, date_to):
    data_frame = pandas.DataFrame(list(data))
    data_frame.columns = ['Менеджер', 
                          'Кол-во симок', 
                          'Суммарная стоимость месячных тарифов',
                          ]

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        date_from = date_from.strftime('%d.%m.%Y')
        date_to = date_to.strftime('%d.%m.%Y')
        data_frame.to_excel(temp_file.name, index=False, sheet_name=f'{date_from} - {date_to}')
        
        return temp_file.name


def extract_digits(input_string):
    return re.sub(r'\D', '', input_string)
