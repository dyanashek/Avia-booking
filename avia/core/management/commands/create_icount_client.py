import requests

from django.core.management import BaseCommand

from core.models import OldSim
from config import (OLD_ICOUNT_COMPANY_ID, OLD_ICOUNT_USERNAME, 
                    OLD_ICOUNT_PASSWORD, ICOUNT_CREATE_USER_ENDPOINT)


class Command(BaseCommand):
    def handle(self, *args, **options):
        for old_sim in OldSim.objects.filter(icount_id=0).all():
            name = old_sim.name
            phone = old_sim.sim_phone
            vat = '0' + phone.lstrip('972')

            data = {
                'cid': OLD_ICOUNT_COMPANY_ID,
                'user': OLD_ICOUNT_USERNAME,
                'pass': OLD_ICOUNT_PASSWORD,
                'client_name': name,
                'first_name': name,
                'mobile': phone,
                'vat_id': vat,
            }
            response = requests.post(ICOUNT_CREATE_USER_ENDPOINT, data=data)
            if response.json().get('client_id'):
                old_sim.icount_id = int(response.json().get('client_id'))
                old_sim.save()
        
        print('done')

