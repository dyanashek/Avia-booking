import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from core.models import UsersSim
from money_transfer.models import Sender, Receiver, Delivery, Status
from money_transfer.utils import update_delivery_pickup_status

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
def stop_status(request):
    stop_id = request.POST.get('id')
    order_id = request.POST.get('order_id')
    driver_comment = request.POST.get('comment')
    try:
        status = request.POST.get('status')
    except:
        status = False

    if order_id and order_id == '3':
        delivery = Delivery.objects.filter(circuit_id=stop_id).first()
        if delivery:
            if status:
                
                try:
                    update_delivery_pickup_status(delivery.pk, driver_comment)
                except:
                    pass

                succeeded = Status.objects.get(slug='finished')
                delivery.status = succeeded
                delivery.status_message = 'Получено от отправителя'
            else:
                attempted = Status.objects.get(slug='attempted')
                delivery.status = attempted
                delivery.status_message = 'Не удалось забрать у отправителя'
            
            delivery.save()
    
    if order_id and order_id == '5':
        users_sim = UsersSim.objects.filter(circuit_id=stop_id).first()
        if users_sim:
            users_sim.circuit_id_collect = None
            users_sim.ready_to_pay = False
            users_sim.pay_date = None
            users_sim.save()
    
    return HttpResponse()