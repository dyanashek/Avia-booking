from django.core.management import BaseCommand

from core.models import UsersSim


class Command(BaseCommand):
    def handle(self, *args, **options):
        for sim in UsersSim.objects.filter(circuit_id_collect__isnull=False, ready_to_pay=False).all():
            print(sim)
            