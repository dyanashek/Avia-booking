import pandas
import os
import datetime

from django.core.management import BaseCommand

from core.models import OldSim, SimFare


class Command(BaseCommand):
    def handle(self, *args, **options):
        OldSim.objects.all().delete()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'old_sims.csv')
        df = pandas.read_csv(file_path)

        counter = 0
        for row in df.itertuples(index=False):
            name = str(row.name).split(' ')[0]
            fare = SimFare.objects.get(price=row.tariff)
            debt = row.balance * (-1)
            phone = row.simcard_mobile
            address = row.tags
            icount_id = int(row.icount_id)

            OldSim.objects.create(
                sim_phone=phone,
                fare=fare,
                address=address,
                name=name,
                debt=debt,
                next_payment=datetime.date(year=2024, month=8, day=26),
                icount_id=icount_id,
            )
            counter += 1
    
        print(f'Перенесено записей: {counter}')

