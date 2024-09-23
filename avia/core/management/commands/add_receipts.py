from django.core.management import BaseCommand
from django.db.models import Q

from core.models import Notification, Receipt

class Command(BaseCommand):
    def handle(self, *args, **options):
        for notification in Notification.objects.filter(text__contains='https:'):
            link = 'https:' + notification.text.split('https:')[-1]
            receipt = Receipt.objects.filter(link=link).first()
            if not receipt:
                Receipt.objects.create(
                    user=notification.user,
                    link=link,
                    notify_time=notification.notify_time,
                    success=notification.notified,
                )
