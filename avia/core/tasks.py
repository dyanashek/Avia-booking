import datetime
import json

from django.db.models import Q
from celery import shared_task

from core.models import UsersSim, TGText, Notification, OldSim
from core.utils import send_message_on_telegram


def add_debt():
    users_sims = UsersSim.objects.filter(next_payment=datetime.datetime.utcnow().date()).select_related('fare').all()
    for users_sim in users_sims:
        price = users_sim.fare.price
        users_sim.debt += price
        users_sim.next_payment = datetime.datetime.utcnow() + datetime.timedelta(days=31)
        users_sim.save()


def add_pay_date():
    users_sims = UsersSim.objects.filter(Q(Q(pay_date__isnull=True) | Q(pay_date__lt=datetime.datetime.utcnow().date())) & 
                                         Q(ready_to_pay=False) & 
                                         Q(debt__gte=200)).all()
    for users_sim in users_sims:
        users_sim.pay_date = datetime.datetime.utcnow().date()
        users_sim.notified = False
        users_sim.circuit_id_collect = None
        users_sim.save()


def search_users_to_notify():
    return UsersSim.objects.filter(
        Q(pay_date=datetime.datetime.utcnow().date()) & 
        Q(ready_to_pay=False) &
        Q(notified=False)).select_related('user', 'fare').all()
    

def notify_users(users_sims):
    for users_sim in users_sims:
        if users_sim.user:
            language = users_sim.user.language
            sim_debt = TGText.objects.get(slug='sim_debt', language=language).text
            fare_text = TGText.objects.get(slug='fare', language=language).text
            fare_price_text = TGText.objects.get(slug='fare_price', language=language).text
            payment_needed = TGText.objects.get(slug='payment_needed', language=language).text

            ready_pay_button = TGText.objects.get(slug='ready_pay_button', language=language).text
            week_later_button = TGText.objects.get(slug='later_week_button', language=language).text
            month_later_button = TGText.objects.get(slug='later_month_button', language=language).text

            message = f'''
                    {sim_debt} {users_sim.sim_phone}:\
                    \n*{users_sim.debt} ₪*\
                    \n\
                    \n*{fare_text}*\
                    \n{users_sim.fare.description}\
                    \n*{fare_price_text} {users_sim.fare.price}₪*\
                    \n\
                    \n{payment_needed}\
                    '''

            
            params = {
                'chat_id': users_sim.user.user_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': json.dumps({
                    'inline_keyboard': [
                        [{'text': ready_pay_button, 'callback_data': 'readypay'}],
                        [{'text': week_later_button, 'callback_data': 'later_week'}],
                        [{'text': month_later_button, 'callback_data': 'later_month'}]
                    ]
                })
            }
            try:
                send_message_on_telegram(params)
                users_sim.notified = True
                users_sim.save()
            except:
                pass


def select_notifications():
    notifications = Notification.objects.filter(Q(notify_time__lte=datetime.datetime.utcnow()) &
                                                Q(notified__isnull=True) &
                                                Q(notify_now=False))
    
    return notifications


# @shared_task
# def add_debt_old_sims():
#     users_sims = OldSim.objects.filter(next_payment=datetime.datetime.utcnow().date(), to_main_bot=False).select_related('fare').all()
#     for users_sim in users_sims:
#         price = users_sim.fare.price
#         users_sim.debt += price
#         users_sim.next_payment = datetime.datetime.utcnow() + datetime.timedelta(days=31)
#         users_sim.save()


@shared_task
def send_notifications():
    notifications = select_notifications()
    for notification in notifications:
        params = {
            'chat_id':  notification.user.user_id,
            'text': notification.text,
        }

        try:
            send_message_on_telegram(params)
            notification.notified = True
        except:
            notification.notified = False
        
        notification.save()


@shared_task
def handle_sims():
    add_debt()
    add_pay_date()
    users_sims = search_users_to_notify()
    notify_users(users_sims)
