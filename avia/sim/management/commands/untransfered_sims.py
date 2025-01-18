import pandas
import os
import datetime

from django.core.management import BaseCommand

from core.models import UsersSim
from sim.models import SimCard


class Command(BaseCommand):
    def handle(self, *args, **options):
        for sim in SimCard.objects.filter(to_main_bot=False):
            if UsersSim.objects.filter(sim_phone=sim.sim_phone).exists():
                print(sim.sim_phone)
        print('done')

