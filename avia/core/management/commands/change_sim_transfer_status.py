import datetime

from django.core.management import BaseCommand

from sim.models import SimCard

class Command(BaseCommand):
    def handle(self, *args, **options):
        sim = SimCard.objects.get(sim_phone='972586787676')
        sim.to_main_bot = False
        sim.save()
            