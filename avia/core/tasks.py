import datetime
import json
import time

from django.db.models import Q
from celery import shared_task

from core.models import UsersSim, TGText, Notification, OldSim, ImprovedNotification, TGUser, Language
from core.utils import send_message_on_telegram, send_improved_message_on_telegram
from sim.models import SimCard

from config import SIM_DEBT_LIMIT


def add_debt():
    users_sims = UsersSim.objects.filter(Q(next_payment=datetime.datetime.utcnow().date()) &
                                         Q(is_stopped=False)).select_related('fare').all()
    for users_sim in users_sims:
        price = users_sim.fare.price
        users_sim.debt += price
        users_sim.next_payment = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        users_sim.save()


def add_pay_date():
    users_sims = UsersSim.objects.filter(Q(Q(pay_date__isnull=True) | Q(pay_date__lt=datetime.datetime.utcnow().date())) & 
                                         Q(ready_to_pay=False) & 
                                         Q(debt__gte=SIM_DEBT_LIMIT)).all()
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
    basic_language = Language.objects.get(slug='rus')
    for users_sim in users_sims:
        if users_sim.user:
            language = users_sim.user.language
            if not language:
                language = basic_language
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
                time.sleep(3)
            except:
                pass


def select_notifications():
    notifications = Notification.objects.filter(Q(notify_time__lte=datetime.datetime.utcnow()) &
                                                Q(notified__isnull=True) &
                                                Q(notify_now=False))
    
    return notifications


@shared_task
def add_debt_old_sims():
    users_sims = OldSim.objects.filter(next_payment=datetime.datetime.utcnow().date(), to_main_bot=False).select_related('fare').all()
    for users_sim in users_sims:
        price = users_sim.fare.price
        users_sim.debt += price
        users_sim.next_payment = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        users_sim.save()


@shared_task
def add_debt_admin_sims():
    users_sims = SimCard.objects.filter(Q(next_payment=datetime.datetime.utcnow().date()) &
                                        Q(to_main_bot=False) &
                                        Q(is_stopped=False)).select_related('fare').all()
    for users_sim in users_sims:
        price = users_sim.fare.price
        users_sim.debt += price
        users_sim.next_payment = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        users_sim.save()


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
        time.sleep(3)


@shared_task
def handle_sims():
    add_debt()
    add_pay_date()
    users_sims = search_users_to_notify()
    notify_users(users_sims)


def search_improved_notifications():
    return ImprovedNotification.objects.filter(
        Q(notify_time__lte=datetime.datetime.utcnow()) & 
        Q(is_valid=True) &
        Q(started=False)).select_related('image').all()
    

def check_improved_notification(notification: ImprovedNotification):
    is_valid = True
    for button in notification.buttons.all():
        if 'https://' not in button.link:
            is_valid = False
            break

    return is_valid
    

def mark_notifications_started(notifications):
    valid_notifications = []
    for notification in notifications:
        is_valid = check_improved_notification(notification)
        if is_valid:
            notification.started = True
            valid_notifications.append(notification)
        else:
            notification.is_valid = False
        
        notification.save()

    return valid_notifications


def select_users_for_notification(notification: ImprovedNotification):
    if notification.target == '1':
        users = [notification.user]
    elif notification.target == '2':
        users = TGUser.objects.all()
    
    return users


def construct_notification_params(notification: ImprovedNotification):
    if notification.image:
        image_path = notification.image.path
        params = {
            'caption': notification.text.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('&nbsp;', ''),
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }

    else:
        image_path = False
        params = {
                'text': notification.text.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('&nbsp;', ''),
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            }
        
    
    if notification.buttons.all():
        buttons = []
        for button in notification.buttons.all():
            buttons.append([{
                'text': button.text,
                'url': button.link,
            }])
        
        params['reply_markup'] = json.dumps({'inline_keyboard': buttons})

    return params, image_path
    

@shared_task
def send_improved_notifications():
    notifications = search_improved_notifications()
    valid_notifications = mark_notifications_started(notifications)

    for notification in valid_notifications:
        users = select_users_for_notification(notification)
        params, image_path = construct_notification_params(notification)
        total_users = len(users)

        notification.total_users = total_users
        notification.save()
        success = False
        for user in users:
            params['chat_id'] = user.user_id

            if image_path:
                with open(image_path, 'rb') as image:
                    files = {
                        'photo': image,
                    }
                    response = send_improved_message_on_telegram(params, files=files)
            
            else:
                response = send_improved_message_on_telegram(params)
            
            notification.total_send_users += 1
            if response:
                try:
                    if response.json().get('ok'):
                        success = True
                        notification.success_users += 1
                except:
                    pass
            
            notification.save()
            time.sleep(3)
        
        notification.notified = success
        notification.save()
