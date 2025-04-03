import re
import datetime
import requests

import config


async def extract_digits(input_string):
    return re.sub(r'\D', '', input_string)


async def extract_tg_id(message):
    pattern = r"TG id: (\d+)"

    match = re.search(pattern, message)

    tg_id = None
    if match:
        tg_id = match.group(1)

    return tg_id


async def validate_phone(phone):
    phone = await extract_digits(phone)
    if len(phone) > 6:
        return phone
    else:
        return False


async def validate_phone_sim(phone):
    phone = await extract_digits(phone)
    if len(phone) > 10 and phone.startswith('972'):
        return phone
    else:
        return False


async def validate_date(input_string):
    date = await extract_digits(input_string)
    try:
        date = datetime.datetime.strptime(date, '%d%m%Y').date()
    except:
        date = None
    
    return date


async def validate_price(input_string):
    try:
        input_string = input_string.replace(',', '.')
        price = float(input_string)
    except:
        return False
    
    if price >= 0:
        return round(price, 2)
    
    return False


async def validate_passport(input_string):
    passport_pattern = r'\b[A-Z]{2}\d{7}\b'
    passports = re.findall(passport_pattern, input_string)

    if passports:
        return passports[0]
    
    return None


async def escape_markdown(text):
    try:
        characters_to_escape = ['_', '*', '[', ']', '`']
        for char in characters_to_escape:
            text = text.replace(char, '\\' + char)
    except:
        pass
    
    return text


async def validate_id(value):
    try:
        return int(value)
    except:
        return False


async def validate_rate(input_string):
    try:
        input_string = input_string.replace(',', '.')
        rate = float(input_string)
    except:
        return False
    
    if rate > 0:
        return round(rate, 2)
    
    return False


async def get_payment_dates():
    print(1)
    days = [1, 10, 20]
    current_date = (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()
    current_year = current_date.year
    current_month = current_date.month
    print(2)
    payment_days = []
    for day in days:
        payment_day = datetime.date(year=current_year, month=current_month, day=day)
        if payment_day > current_date:
            if day < 10:
                day = f'0{day}'
            if current_month < 10:
                current_month = f'0{current_month}'
            payment_days.append(f'{day}.{current_month}.{current_year}')
    print(3)
    current_year = current_date.year
    current_month = current_date.month
    print(4)        
    for day in days:
        payment_day = datetime.date(year=current_year, month=current_month, day=day)
        if payment_day <= current_date:
            if current_month == 12:
                payment_month = 1
                payment_year = current_year + 1
            else:
                payment_month = current_month + 1
                payment_year  = current_year
            
            if day < 10:
                day = f'0{day}'
            if payment_month < 10:
                payment_month = f'0{payment_month}'
            payment_days.append(f'{day}.{payment_month}.{payment_year}')
    print(5)
    return payment_days


async def send_tg_message(params, token=config.TELEGRAM_TOKEN):
    endpoint = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        response = requests.post(endpoint, params=params)
    except:
        pass
        
    return response
    