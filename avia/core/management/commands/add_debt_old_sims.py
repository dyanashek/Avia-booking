import pandas
import os
import datetime

from django.core.management import BaseCommand

from core.models import OldSim


class Command(BaseCommand):
    def handle(self, *args, **options):
        for old_sim in OldSim.objects.all():
            debt = old_sim.fare.price
            old_sim.debt += debt
            old_sim.save()
        
        print('done')

