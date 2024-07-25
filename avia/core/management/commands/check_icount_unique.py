from django.core.management import BaseCommand
from django.db.models import Count

from core.models import OldSim


class Command(BaseCommand):
    def handle(self, *args, **options):
        clients_all = OldSim.objects.count()
        clients_unique = OldSim.objects.values('icount_id').annotate(count=Count('id')).count()

        if clients_all == clients_unique:
            print('All clients are unique!')
        else:
            duplicates = (
                OldSim.objects
                .values('icount_id')
                .annotate(count=Count('icount_id'))
                .filter(count__gt=1)
            )

            for duplicate in duplicates:
                print(f"Client ID: {duplicate['icount_id']} not unique.")
