import pandas
import os
import requests
import re

from django.core.management import BaseCommand

from core.models import OldSim, SimFare
from config import OLD_ICOUNT_COMPANY_ID, OLD_ICOUNT_USERNAME, OLD_ICOUNT_PASSWORD

class Command(BaseCommand):
    def printProgressBar(self, iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
        # Print New Line on Complete
        if iteration == total:
            print()

    def handle(self, *args, **options):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'old_sims.csv')
        df = pandas.read_csv(file_path)

        counter = 0
        progress_bar_counter_total = df.shape[0]
        progress_bar_counter = 0
        self.stdout.write(self.style.SUCCESS('Извлечение id...'))
        self.printProgressBar(progress_bar_counter, progress_bar_counter_total, prefix = 'Загрузка:', suffix = '', length = 50)
        for row in df.itertuples(index=False):
            try:
                invoice = row.last_invoice
                old_sim = OldSim.objects.get(sim_phone=str(row.simcard_mobile))

                try:
                    int(str(invoice))
                    is_int = True
                except:
                    is_int = False

                if is_int:
                    try:
                        old_sim.icount_id = int(str(invoice))
                        old_sim.save()
                        counter += 1
                    except:
                        pass
                    

                elif len(str(invoice)) > 3:
                    try:
                        response = requests.get(str(invoice))
                        content_disposition = response.headers.get('Content-Disposition', '')     
                        match = re.search(r'filename=".*?(\d+).*?"', content_disposition)
                        doc_num = int(match.group(1))
                        endpoint = 'https://api.icount.co.il/api/v3.php/doc/info'
                        params = {
                            'cid': OLD_ICOUNT_COMPANY_ID,
                            'user': OLD_ICOUNT_USERNAME,
                            'pass': OLD_ICOUNT_PASSWORD,
                            'doctype': 'invrec',
                            'docnum': doc_num,
                            'get_custom_info': True,
                        }
                        response = requests.post(endpoint, json=params)
                        old_sim.icount_id = int(response.json().get('doc_info').get('client_id'))
                        old_sim.save()
                        counter += 1
                    except:
                        pass
                else:
                    try:
                        endpoint = 'https://api.icount.co.il/api/v3.php/client/info'
                        params = {
                            'cid': OLD_ICOUNT_COMPANY_ID,
                            'user': OLD_ICOUNT_USERNAME,
                            'pass': OLD_ICOUNT_PASSWORD,
                            'client_name': row.name,
                        }
                        response = requests.post(endpoint, json=params)
                        phone = str(row.simcard_mobile).lstrip('972')
                        if response.json().get('status') and ((response.json().get('mobile') and phone in response.json().get('mobile')) or (response.json().get('vat_id') and phone in response.json().get('vat_id'))):
                            old_sim.icount_id = int(response.json().get('client_id'))
                            old_sim.save()
                            counter += 1
                        else:
                            params = {
                                'cid': OLD_ICOUNT_COMPANY_ID,
                                'user': OLD_ICOUNT_USERNAME,
                                'pass': OLD_ICOUNT_PASSWORD,
                                'vat_id': phone,
                            }
                            response = requests.post(endpoint, json=params)
                            if response.json().get('status'):
                                old_sim.icount_id = int(response.json().get('client_id'))
                                old_sim.save()
                                counter += 1
                            else:
                                params = {
                                'cid': OLD_ICOUNT_COMPANY_ID,
                                'user': OLD_ICOUNT_USERNAME,
                                'pass': OLD_ICOUNT_PASSWORD,
                                'vat_id': f'0{phone}',
                                }
                                response = requests.post(endpoint, json=params)
                                if response.json().get('status'):
                                    old_sim.icount_id = int(response.json().get('client_id'))
                                    old_sim.save()
                                    counter += 1
                                else:
                                    params = {
                                    'cid': OLD_ICOUNT_COMPANY_ID,
                                    'user': OLD_ICOUNT_USERNAME,
                                    'pass': OLD_ICOUNT_PASSWORD,
                                    'client_name': phone,
                                    }
                                    response = requests.post(endpoint, json=params)
                                    if response.json().get('status'):
                                        old_sim.icount_id = int(response.json().get('client_id'))
                                        old_sim.save()
                                        counter += 1
                                    else:
                                        params = {
                                        'cid': OLD_ICOUNT_COMPANY_ID,
                                        'user': OLD_ICOUNT_USERNAME,
                                        'pass': OLD_ICOUNT_PASSWORD,
                                        'client_name': f'0{phone}',
                                        }
                                        response = requests.post(endpoint, json=params)
                                        if response.json().get('status'):
                                            old_sim.icount_id = int(response.json().get('client_id'))
                                            old_sim.save()
                                            counter += 1
                    except:
                        pass
            except:
                pass
            
            progress_bar_counter += 1
            self.printProgressBar(progress_bar_counter, progress_bar_counter_total, prefix = 'Извлечение:', suffix = '', length = 50)

        self.stdout.write(self.style.SUCCESS(f"Извлечено id: {counter}"))

