from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')

app = Celery('AVIA')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True
app.conf.beat_schedule = {
    'run-scheduler-every-five-minutes': {
        'task': 'core.tasks.send_notifications',
        'schedule': crontab(minute='*/5'),  
    },
    'run-scheduler-every-day': {
        'task': 'core.tasks.handle_sims',
        'schedule': crontab(hour=7, minute=0),  
    },
    'run-scheduler-every-day-adminsims': {
        'task': 'core.tasks.add_debt_admin_sims',
        'schedule': crontab(hour=6, minute=0),  
    },
    'run-scheduler-every-one-minute': {
        'task': 'core.tasks.send_improved_notifications',
        'schedule': crontab(minute='*/2'),  
    },
}

app.autodiscover_tasks()