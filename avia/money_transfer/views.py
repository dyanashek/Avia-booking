import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404

from core.models import UsersSim
from money_transfer.models import Sender, Receiver, Delivery, Status, Rate, Commission
from money_transfer.utils import (update_delivery_pickup_status, update_credit_status, send_pickup_address,
                                  delivery_to_gspread)
from core.utils import send_message_on_telegram
from drivers.utils import construct_collect_sim_money_message, construct_delivery_sim_message

from config import TELEGRAM_DRIVERS_TOKEN

# Create your views here.
def get_sender_addresses(request):
    sender_id = request.GET.get('sender_id')
    if sender_id:
        addresses = Sender.objects.get(id=sender_id).addresses.all()
        address_options = '<option value="">---------</option>'
        for address in addresses:
            address_options += f'<option value="{address.id}">{address.address}</option>'

        return JsonResponse({'addresses': address_options})


def get_sender_receivers(request):
    sender_id = request.GET.get('sender_id')
    if sender_id:
        receivers = Sender.objects.get(id=sender_id).receivers.all()
        receivers_options = '<option value="">---------</option>'
        for receiver in receivers:
            receivers_options += f'<option value="{receiver.id}">{receiver}</option>'
            
        return JsonResponse({'receivers': receivers_options})


def get_receiver_addresses(request):
    receiver_id = request.GET.get('receiver_id')
    if receiver_id:
        addresses = Receiver.objects.get(id=receiver_id).addresses.all()
        address_options = '<option value="">---------</option>'
        for address in addresses:
            address_options += f'<option value="{address.id}">{address.address}</option>'

        return JsonResponse({'addresses': address_options})


@csrf_exempt
def calculate_commission(request):
    try:
        usd_amount = int(request.GET.get('usd_amount'))
    except:
        usd_amount = 0
    
    try:
        ils_amount = int(request.GET.get('ils_amount'))
    except:
        ils_amount = 0

    ils_rate = Rate.objects.get(slug='usd-ils').rate
    usd_amount = round(usd_amount + ils_amount / ils_rate,2)

    commission = Commission.objects.filter(Q(Q(low_value__lte=usd_amount) & Q(high_value__gte=usd_amount)) | 
                                Q(Q(low_value__lte=usd_amount) & Q(high_value__isnull=True))).first()

    if commission:
        unit = commission.unit
        value = commission.value

        if unit == 1:
            commission = round(usd_amount * ils_rate * (value / 100), 2)
        else:
            commission = value
    else:
        commission = 0

    return JsonResponse({'total_usd': f'{usd_amount}$', 'commission': f'{commission}₪'})


@csrf_exempt
def stop_status(request):
    #? 1 - забор билета (создан через бота)
    #? 2 - забор посылки (создана через бота)
    #? 3 - забор денег для трансфера в Узбекистан (через админку)
    #? 4 - доставка симки (через бота)
    #? 5 - забор денег за симку (через бота)

    stop_id = request.POST.get('id')
    order_id = request.POST.get('order_id')
    driver_comment = request.POST.get('comment')
    driver_id = request.POST.get('driver')
    try:
        status = request.POST.get('status')
    except:
        status = False

    if order_id and order_id == '3':
        delivery = Delivery.objects.filter(circuit_id=stop_id).first()
        if delivery:
            if status:
                succeeded = Status.objects.get(slug='finished')
                delivery.status = succeeded
                delivery.status_message = 'Получено от отправителя'

                for transfer in delivery.transfers.filter(credit=True):
                    transfer.credit = False
                    transfer.save()
                    try:
                        update_credit_status(transfer.id)
                    except:
                        pass

                try:
                    update_delivery_pickup_status(delivery.pk, driver_comment)
                except:
                    pass
            else:
                attempted = Status.objects.get(slug='attempted')
                delivery.status = attempted
                delivery.status_message = 'Не удалось забрать у отправителя'

            delivery.save()

    elif order_id and order_id == '4' and status:

        users_sim = UsersSim.objects.filter(circuit_id=stop_id).first()
        if users_sim:
            params = construct_delivery_sim_message(users_sim, driver_id)
            if params:
                try:
                    send_message_on_telegram(params, TELEGRAM_DRIVERS_TOKEN)
                except:
                    pass

    elif order_id and order_id == '5' and status:
        users_sim = UsersSim.objects.filter(circuit_id_collect=stop_id).first()
        if users_sim:
            users_sim.circuit_id_collect = None
            users_sim.ready_to_pay = False
            users_sim.pay_date = None
            users_sim.save()

            params = construct_collect_sim_money_message(users_sim, driver_id)
            if params:
                try:
                    send_message_on_telegram(params, TELEGRAM_DRIVERS_TOKEN)
                except:
                    pass
    
    return HttpResponse()


def delivery_resend_circuit(request, pk):
    delivery = get_object_or_404(Delivery, id=pk)

    codes = ''
    for transfer in delivery.transfers.all():
        codes += f'{transfer.id}, '
    
    codes = codes.rstrip(', ')

    if delivery.circuit_api is False:
        stop_id = send_pickup_address(delivery.sender, delivery, codes)
        if stop_id:
            gspread_error = False
            delivery.circuit_api = True
            api_status = Status.objects.get(slug='api')
            delivery.circuit_id = stop_id
            delivery.circuit_api = True
            delivery.status = api_status

            if 'Ошибка при записи в гугл таблицу' in delivery.status_message:
                gspread_error = True

            delivery.status_message = 'Доставка передана в Circuit.'

            if gspread_error:
                delivery.status_message += ' Ошибка при записи в гугл таблицу.'

            delivery.save()


    return redirect('/admin/money_transfer/delivery/')


def delivery_resend_gspread(request, pk):
    delivery = get_object_or_404(Delivery, id=pk)

    if delivery.gspread_api is False:
        try:
            delivery_to_gspread(delivery)
            delivery.gspread_api = True

            if 'Ошибка при записи в гугл таблицу' in delivery.status_message:
                delivery.status_message = delivery.status_message.replace('Ошибка при записи в гугл таблицу.', '')

            delivery.save()
        except:
            pass


    return redirect('/admin/money_transfer/delivery/')