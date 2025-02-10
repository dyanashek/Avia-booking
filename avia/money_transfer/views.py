import json
import requests
import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404

from sim.models import Collect
from core.models import UsersSim
from errors.models import AppError
from money_transfer.models import Sender, Receiver, Delivery, Status, Rate, Commission, Report
from money_transfer.utils import (update_delivery_pickup_status, update_credit_status, send_pickup_address,
                                  delivery_to_gspread)
from core.utils import send_message_on_telegram
from drivers.utils import construct_collect_sim_money_message, construct_delivery_sim_message
from money_transfer.additional_utils import report_to_db, stop_to_report, extract_driver

from config import TELEGRAM_DRIVERS_TOKEN, DUPLICATE_SIM_MONEY, TELEGRAM_BOT

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
    #? 6 - забор билета (создан через админку)
    #? 7 - забор посылки (создан через админку)

    stop_id = request.POST.get('id')
    order_id = request.POST.get('order_id')
    driver_comment = request.POST.get('comment')
    driver_id = request.POST.get('driver')
    status = request.POST.get('status', 'false')
    status = status.lower()

    if order_id and order_id == '3' and status == 'true':
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
                    except Exception as ex:
                        try:
                            AppError.objects.create(
                                source='5',
                                error_type='6',
                                description=f'Не удалось перенести данные в гугл таблицу (отправка денег, изменение статуса кредита на "не выдано в кредит"). {transfer.id}. {ex}',
                            )
                        except:
                            pass

                try:
                    update_delivery_pickup_status(delivery.pk, driver_comment)
                except Exception as ex:
                    try:
                        AppError.objects.create(
                            source='5',
                            error_type='6',
                            description=f'Не удалось перенести данные в гугл таблицу (отправка денег, изменение статуса на "получено"). {delivery.id}. {ex}',
                        )
                    except:
                        pass
            else:
                attempted = Status.objects.get(slug='attempted')
                delivery.status = attempted
                delivery.status_message = 'Не удалось забрать у отправителя'

            delivery.save()

            try:
                stop_to_report(stop_id)
            except:
                pass

    elif order_id and order_id == '4' and status == 'true':

        users_sim = UsersSim.objects.filter(circuit_id=stop_id).first()
        if users_sim:
            try:
                curr_driver = extract_driver(stop_id)
                if curr_driver:
                    Collect.objects.create(
                        sim=users_sim,
                        driver=curr_driver,
                    )
                else:
                    try:
                        AppError.objects.create(
                            source='5',
                            error_type='9',
                            description=f'Не удалось выявить водителя и создать сущность забора денег за симкарту (первичный). {users_sim.sim_phone}.',
                        )
                    except:
                        pass
            except Exception as ex:
                try:
                    AppError.objects.create(
                        source='5',
                        error_type='9',
                        description=f'Не удалось выявить водителя и создать сущность забора денег за симкарту (первичный). {users_sim.sim_phone}. {ex}',
                    )
                except:
                    pass

            params = construct_delivery_sim_message(users_sim, driver_id)
            if params:
                try:
                    send_message_on_telegram(params, TELEGRAM_DRIVERS_TOKEN)
                    params['chat_id'] = DUPLICATE_SIM_MONEY
                    send_message_on_telegram(params, TELEGRAM_DRIVERS_TOKEN)
                except:
                    pass

    elif order_id and order_id == '5' and status == 'true':
        users_sim = UsersSim.objects.filter(circuit_id_collect=stop_id).first()
        if users_sim:
            try:
                curr_driver = extract_driver(stop_id)
                if curr_driver:
                    Collect.objects.create(
                        sim=users_sim,
                        driver=curr_driver,
                    )
                else:
                    try:
                        AppError.objects.create(
                            source='5',
                            error_type='9',
                            description=f'Не удалось выявить водителя и создать сущность забора денег за симкарту (вторичный). {users_sim.sim_phone}.',
                        )
                    except:
                        pass
            except Exception as ex:
                try:
                    AppError.objects.create(
                        source='5',
                        error_type='9',
                        description=f'Не удалось выявить водителя и создать сущность забора денег за симкарту (вторичный). {users_sim.sim_phone}. {ex}',
                    )
                except:
                    pass

            users_sim.circuit_id_collect = None
            users_sim.ready_to_pay = False
            users_sim.pay_date = None
            users_sim.save()

            params = construct_collect_sim_money_message(users_sim, driver_id)
            if params:
                try:
                    send_message_on_telegram(params, TELEGRAM_DRIVERS_TOKEN)
                    params['chat_id'] = DUPLICATE_SIM_MONEY
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
            delivery.invite_client = f'https://t.me/{TELEGRAM_BOT}?start=money{delivery.id}'

            if 'Ошибка при записи в гугл таблицу' in delivery.status_message:
                gspread_error = True

            delivery.status_message = 'Доставка передана в Circuit.'

            if gspread_error:
                delivery.status_message += ' Ошибка при записи в гугл таблицу.'

            delivery.save()

            if delivery.sender.user:
                message = f'''
                            \nСоздан новый перевод!\
                            \n\
                            \n*Отправление:*\
                            \nНомер отправителя: *{delivery.sender.phone}*\
                            '''
                if delivery.ils_amount:
                    message += f'\nСумма в ₪: *{int(delivery.ils_amount)}*'
                
                message += f'''\nСумма в $: *{int(delivery.usd_amount)}*\
                            \nКомиссия в ₪: *{int(delivery.commission)}*\
                            '''

                if delivery.ils_amount:     
                    message += f'\nИтого в $: *{int(delivery.total_usd)}*'
                
                message += f'\n\n*Получатели:*'

                for num, transfer in enumerate(delivery.transfers.all()):
                    if transfer.pick_up:
                        pick_up = 'да'
                    else:
                        pick_up = 'нет'

                    transfer_message = f'''\n{num + 1}. Код получения: *{transfer.id}*\
                                        \nНомер получателя: *{transfer.receiver.phone}*\
                                        \nСумма: *{int(transfer.usd_amount)} $*\
                                        \nДоставка: *{pick_up}*\
                                        '''
                    
                    if transfer.address:
                        address = transfer.address.address
                        transfer_message += f'\nАдрес: *{address}*'
                    transfer_message += '\n'
                    message += transfer_message

                params = {
                    'chat_id': delivery.sender.user.user_id,
                    'text': message,
                    'parse_mode': 'Markdown',
                }

                response = send_message_on_telegram(params)
                if response and response.ok:
                    delivery.invite_client = f'отправлено: https://t.me/{TELEGRAM_BOT}?start=money{delivery.id}'
                    delivery.save(update_fields=['invite_client',])

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
        except Exception as ex:
            try:
                AppError.objects.create(
                    source='5',
                    error_type='6',
                    description=f'Не удалось перенести данные в гугл таблицу (отправка денег, создание через кнопку). {delivery.id}. {ex}',
                )
            except:
                pass


    return redirect('/admin/money_transfer/delivery/')


@csrf_exempt
def construct_report(request):
    page_token = 'first'
    data = {
            'maxPageSize': 10,
        }
    report = {}
    while page_token:
        if page_token != 'first':
            data['pageToken'] = page_token
        response = requests.get(settings.GET_STOPS_ENDPOINT, headers=settings.CURCUIT_HEADER, params=data)

        for stop in response.json().get('stops'):
            success = stop.get('deliveryInfo').get('succeeded')
            order_code = stop.get('orderInfo').get('sellerOrderId')

            if success and order_code == '3':
                timestamp = stop.get('deliveryInfo').get('attemptedAt')
                delivery_date = (datetime.datetime.utcfromtimestamp(timestamp) + datetime.timedelta(hours=3)).date()
                state = stop.get('deliveryInfo').get('state')
                delivery_id = stop.get('id')
                
                try:
                    curr_delivery = Delivery.objects.get(circuit_id=delivery_id)
                except:
                    curr_delivery = None

                if delivery_date not in report:
                    report[delivery_date] = {
                        'first_driver': {
                            'usd': 0,
                            'ils': 0,
                            'commission': 0,
                            'total_points': 0,
                        }, 
                        'second_driver': {
                            'usd': 0,
                            'ils': 0,
                            'commission': 0,
                            'total_points': 0,
                        }, 
                        'third_driver': {
                            'usd': 0,
                            'ils': 0,
                            'commission': 0,
                            'total_points': 0,
                        }, 
                        }
                if curr_delivery:
                    if state == 'delivered_to_recipient':
                        driver_name = 'first_driver'
                    elif state == 'delivered_to_third_party': 
                        driver_name = 'second_driver'
                    elif state == 'delivered_to_mailbox':
                        driver_name = 'third_driver'

                    report[delivery_date][driver_name]['usd'] += curr_delivery.usd_amount
                    report[delivery_date][driver_name]['ils'] += curr_delivery.ils_amount
                    report[delivery_date][driver_name]['commission'] += curr_delivery.commission
                    report[delivery_date][driver_name]['total_points'] += 1

        page_token = response.json().get('nextPageToken')

    report_to_db(report)
    return JsonResponse({'done': True})


class TransferDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'transfer_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        date_today = datetime.datetime.utcnow()
        date_before = date_today - datetime.timedelta(days=7)
        date_today_text = date_today.strftime("%Y-%m-%d")
        date_before_text = date_before.strftime("%Y-%m-%d")
        queryset = Delivery.objects.filter(status__isnull=False).order_by('-created_at').all()
        date_from = self.request.GET.get('date-from', date_before_text)
        if date_from:
            context['date_from'] = date_from
            date_from = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
            queryset = queryset.filter(created_at__date__gte=date_from)
        date_to = self.request.GET.get('date-to', date_today_text)
        if date_to:
            context['date_to'] = date_to
            date_to = datetime.datetime.strptime(date_to, "%Y-%m-%d").date()
            queryset = queryset.filter(created_at__date__lte=date_to)

        context["deliveries"] = queryset.distinct()
        context['page_active'] = 'money'

        return context
