import pandas
import os

from django.core.management import BaseCommand

from core.models import OldSim


class Command(BaseCommand):
    def handle(self, *args, **options):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'old_sims.csv')
        df = pandas.read_csv(file_path)
        df['icount_id'] = ''
        counter = 0

        for index, row in df.iterrows():
            phone = row['simcard_mobile']
            old_sim = OldSim.objects.get(sim_phone=phone)
            df.at[index, 'icount_id'] = old_sim.icount_id
            counter += 1

        df.to_csv(file_path, index=False)
        print(f'Перенесено id: {counter}')

