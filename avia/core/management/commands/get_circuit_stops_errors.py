import requests
import pprint

from django.conf import settings
from django.core.management import BaseCommand

from core.models import UsersSim
from shop.models import Order, TopupRequest, TopupRequestStatus, OrderStatus


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user_sim in UsersSim.objects.filter(ready_to_pay=True).all():
            if user_sim.circuit_id_collect:
                url = f'https://api.getcircuit.com/public/v0.2b/{user_sim.circuit_id_collect}'
            elif user_sim.circuit_id:
                url = f'https://api.getcircuit.com/public/v0.2b/{user_sim.circuit_id}'
            else:
                print(f'{user_sim.sim_phone} - no circuit id')
                continue
            
            try:
                response = requests.get(url, headers=settings.CURCUIT_HEADER)
                attempted = response.json().get('deliveryInfo').get('attempted')
                succeeded = response.json().get('deliveryInfo').get('succeeded')

                if attempted or succeeded:
                    print(f'{user_sim.sim_phone} - attempted: {attempted} - succeeded: {succeeded}')
            except:
                if user_sim.circuit_id_collect:
                    print(f'{user_sim.sim_phone} - {user_sim.circuit_id_collect} - error')
                elif user_sim.circuit_id:
                    print(f'{user_sim.sim_phone} - {user_sim.circuit_id} - error')
                else:
                    print(f'{user_sim.sim_phone} - no circuit id')

        print('-' * 50)
        print('Topup requests:')

        for topup in TopupRequest.objects.filter(status=TopupRequestStatus.Awaiting, circuit_id__isnull=False).all():
            if topup.circuit_id:
                url = f'https://api.getcircuit.com/public/v0.2b/{topup.circuit_id}'
                try:
                    response = requests.get(url, headers=settings.CURCUIT_HEADER)
                    succeeded = response.json().get('deliveryInfo').get('succeeded')
                    attempted = response.json().get('deliveryInfo').get('attempted')
                except:
                    succeeded = False
                    attempted = False

                if succeeded or attempted:
                    print(f'{topup.user.username} - {topup.circuit_id} - succeeded: {succeeded} - attempted: {attempted}')

        print('-' * 50)
        print('Orders:')

        for order in Order.objects.filter(status=OrderStatus.AwaitingDelivery, circuit_id__isnull=False).all():
            if order.circuit_id:
                url = f'https://api.getcircuit.com/public/v0.2b/{order.circuit_id}'
                try:
                    response = requests.get(url, headers=settings.CURCUIT_HEADER)
                    succeeded = response.json().get('deliveryInfo').get('succeeded')
                    attempted = response.json().get('deliveryInfo').get('attempted')
                except:
                    succeeded = False
                    attempted = False

                if succeeded or attempted:
                    print(f'{order.user.username} - {order.circuit_id} - succeeded: {succeeded} - attempted: {attempted}')
