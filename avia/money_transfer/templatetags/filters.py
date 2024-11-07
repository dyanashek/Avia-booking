import datetime
from django import template

register = template.Library()


@register.filter
def to_int(value):
    try:
        return int(value)
    except:
        return value
    

@register.filter
def israel_time(date):
    date = date + datetime.timedelta(hours=3)
    return date.strftime('%d.%m.%Y %H:%M')
    

@register.filter
def get_driver(value):
    drivers = {
        '1': 'Первый водитель',
        '2': 'Второй водитель',
        '3': 'Третий водитель',
    }

    return drivers.get(value, 'Первый водитель')
    