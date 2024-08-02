from django.core.management import BaseCommand
from django.db.models import Q

from money_transfer.models import Delivery, Rate

class Command(BaseCommand):
    def handle(self, *args, **options):
        for delivery in Delivery.objects.all():
            if not delivery.rate:
                delivery.rate = Rate.objects.get(slug='usd-ils').rate
                delivery.save()
                
        print('done')

