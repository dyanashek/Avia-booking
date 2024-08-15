from django.core.management import BaseCommand
from django.db.models import Q

from money_transfer.models import Delivery

class Command(BaseCommand):
    def handle(self, *args, **options):
        delivery = Delivery.objects.get(id=104)
        delivery.ils_amount = 3700
        delivery.save()
        print(delivery.created_at)
