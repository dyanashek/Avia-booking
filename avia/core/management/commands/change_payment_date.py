import datetime

from django.core.management import BaseCommand

from sim.models import SimCard

class Command(BaseCommand):
    def handle(self, *args, **options):
        for sim in SimCard.objects.all():
            sim.next_payment = datetime.date(2024, 9, 26)
            sim.save()
