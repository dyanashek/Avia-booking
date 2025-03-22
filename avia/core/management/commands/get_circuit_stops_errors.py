import requests
import pprint

from django.conf import settings
from django.core.management import BaseCommand

from core.models import UsersSim


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
                    