import requests
import datetime

from django.conf import settings

from money_transfer.models import Delivery, Report


def report_to_db(report: dict):
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


def stop_to_report(stop_id):
    response = requests.get(f'{settings.CURCUIT_END_POINT}/{stop_id}', headers=settings.CURCUIT_HEADER)
    stop = response.json()

    success = stop.get('deliveryInfo').get('succeeded')
    order_code = stop.get('orderInfo').get('sellerOrderId')

    if success and order_code == '3':
        timestamp = stop.get('deliveryInfo').get('attemptedAt')
        delivery_date = (datetime.datetime.utcfromtimestamp(timestamp) + datetime.timedelta(hours=3)).date()
        state = stop.get('deliveryInfo').get('state')

        try:
            curr_delivery = Delivery.objects.get(circuit_id=stop_id)
        except:
            curr_delivery = None

        if curr_delivery:
            report, _ = Report.objects.get_or_create(report_date=delivery_date)
            if state == 'delivered_to_recipient':
                curr_delivery.driver = '1'
                report.first_driver_usd += curr_delivery.usd_amount
                report.first_driver_ils += curr_delivery.ils_amount
                report.first_driver_commission += curr_delivery.commission
                report.first_driver_points += 1
            elif state == 'delivered_to_third_party': 
                curr_delivery.driver = '2'
                report.second_driver_usd += curr_delivery.usd_amount
                report.second_driver_ils += curr_delivery.ils_amount
                report.second_driver_commission += curr_delivery.commission
                report.second_driver_points += 1
            elif state == 'delivered_to_mailbox':
                curr_delivery.driver = '3'
                report.third_driver_usd += curr_delivery.usd_amount
                report.third_driver_ils += curr_delivery.ils_amount
                report.third_driver_commission += curr_delivery.commission
                report.third_driver_points += 1

            curr_delivery.save()
            report.save()
            