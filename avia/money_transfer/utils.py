import os
import tempfile
import requests
import datetime

import pandas
import gspread
from openpyxl import Workbook
from django.conf import settings


service_acc = gspread.service_account(filename=settings.GSPREAD_CONFIG)
sheet = service_acc.open(settings.SPREAD_NAME)
work_sheet = sheet.worksheet(settings.MONEY_TRANSFER_LIST)


def send_pickup_address(sender, delivery):
    items = []
    if delivery.usd_amount:
        items.append(f'{delivery.usd_amount}$')
    if delivery.ils_amount:
        items.append(f'{delivery.ils_amount}₪')
    if delivery.commission:
        items.append(f'комиссия: {delivery.commission}₪')

    notes = 'Отправка денег, '
    notes += ', '.join(items)
    
    data = {
        'address': {
            'addressLineOne': delivery.sender_address.address,
            'country': 'Israel',
        },
        'recipient': {
            'name': sender.name,
            'phone': sender.phone,
            'externalId': str(delivery.id),
        },
        'orderInfo': {
            'products': items,
            'sellerOrderId': '3',
        },
        'activity': 'pickup',
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
        else:
            stop_id = False
    else:
        stop_id = False

    return stop_id
        

def get_first_empty_row():
    return len(work_sheet.col_values(1)) + 1


def get_first_delivery_row(delivery_id):
    try:
        return work_sheet.col_values(1).index(delivery_id) + 1
    except:
        return False


def delivery_to_gspred(delivery):
    delivery_data = []
    for num, transfer in enumerate(delivery.transfers.all()):
        pickup = 'Нет'
        address = ''
        if transfer.pick_up:
            pickup = 'Да'
            address = transfer.address.address
        if num == 0:
            transfer_data = [
                str(delivery.pk),
                '',
                '',
                str(transfer.pk),
                delivery.sender.name,
                delivery.sender_address.address,
                delivery.sender.phone,
                delivery.usd_amount,
                delivery.ils_amount,
                delivery.commission,
                transfer.receiver.name,
                transfer.receiver.phone,
                pickup,
                address,
                transfer.usd_amount,
            ]
        else:
            transfer_data = [
                str(delivery.pk),
                '',
                '',
                str(transfer.pk),
                '',
                '',
                '',
                '',
                '',
                '',
                transfer.receiver.name,
                transfer.receiver.phone,
                pickup,
                address,
                transfer.usd_amount,
            ]
        
        delivery_data.append(transfer_data)

    first_row = get_first_empty_row()
    end_row = first_row + len(delivery_data) - 1
    work_sheet.update(f"A{first_row}:O{end_row}", delivery_data)


def update_delivery_pickup_status(delivery_id, comment):
    row_num = get_first_delivery_row(str(delivery_id))
    date = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
    work_sheet.update(f"B{row_num}:X{row_num}", [[date, comment]])


def create_excel_file(data, date_from, date_to):
    data_frame = pandas.DataFrame(list(data))
    data_frame.columns = ['Менеджер', 
                          'Кол-во успешных переводов', 
                          'Комиссия с успешных переводов', 
                          'Кол-во запланированных переводов', 
                          'Комиссия с запланированных переводов']

    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        date_from = date_from.strftime('%d.%m.%Y')
        date_to = date_to.strftime('%d.%m.%Y')
        data_frame.to_excel(temp_file.name, index=False, sheet_name=f'{date_from} - {date_to}')
        
        return temp_file.name
