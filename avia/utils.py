import re
import datetime


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