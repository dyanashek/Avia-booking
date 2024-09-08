import requests
import datetime

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q

from money_transfer.models import Delivery, Report

class Command(BaseCommand):
    def _report_to_db(self, report: dict):
        for report_date, data in report.items():
            curr_report, _ = Report.objects.get_or_create(report_date=report_date)
            
            curr_report.first_driver_usd = data['first_driver']['usd']
            curr_report.first_driver_ils = data['first_driver']['ils']
            curr_report.first_driver_commission = data['first_driver']['commission']
            curr_report.first_driver_points = data['first_driver']['total_points']

            curr_report.second_driver_usd = data['second_driver']['usd']
            curr_report.second_driver_ils = data['second_driver']['ils']
            curr_report.second_driver_commission = data['second_driver']['commission']
            curr_report.second_driver_points = data['second_driver']['total_points']

            curr_report.third_driver_usd = data['second_driver']['usd']
            curr_report.third_driver_ils = data['second_driver']['ils']
            curr_report.third_driver_commission = data['second_driver']['commission']
            curr_report.third_driver_points = data['second_driver']['total_points']

            curr_report.save()


    def handle(self, *args, **options):
        page_token = 'first'
        data = {
                'maxPageSize': 10,
            }
        report = {}
        while page_token:
            if page_token != 'first':
                data['pageToken'] = page_token
            response = requests.get(settings.GET_STOPS_ENDPOINT, headers=settings.CURCUIT_HEADER, params=data)

            for stop in response.json().get('stops'):
                success = stop.get('deliveryInfo').get('succeeded')
                order_code = stop.get('orderInfo').get('sellerOrderId')

                if success and order_code == '3':
                    timestamp = stop.get('deliveryInfo').get('attemptedAt')
                    delivery_date = (datetime.datetime.utcfromtimestamp(timestamp) + datetime.timedelta(hours=3)).date()
                    state = stop.get('deliveryInfo').get('state')
                    delivery_id = stop.get('id')
                    
                    try:
                        curr_delivery = Delivery.objects.get(circuit_id=delivery_id)
                    except:
                        curr_delivery = None

                    if delivery_date not in report:
                        report[delivery_date] = {
                            'first_driver': {
                                'usd': 0,
                                'ils': 0,
                                'commission': 0,
                                'total_points': 0,
                            }, 
                            'second_driver': {
                                'usd': 0,
                                'ils': 0,
                                'commission': 0,
                                'total_points': 0,
                            }, 
                            'third_driver': {
                                'usd': 0,
                                'ils': 0,
                                'commission': 0,
                                'total_points': 0,
                            }, 
                            }
                    if curr_delivery:
                        if state == 'delivered_to_recipient':
                            driver_name = 'first_driver'
                        elif state == 'delivered_to_third_party': 
                            driver_name = 'second_driver'
                        elif state == 'delivered_to_mailbox':
                            driver_name = 'third_driver'

                        report[delivery_date][driver_name]['usd'] += curr_delivery.usd_amount
                        report[delivery_date][driver_name]['ils'] += curr_delivery.ils_amount
                        report[delivery_date][driver_name]['commission'] += curr_delivery.commission
                        report[delivery_date][driver_name]['total_points'] += 1

            page_token = response.json().get('nextPageToken')

        self._report_to_db(report)

