import re
import datetime


def extract_digits(input_string):
    return re.sub(r'\D', '', input_string)


def validate_phone(phone):
    phone = extract_digits(phone)
    if len(phone) > 6:
        return phone
    else:
        return False


def validate_date(input_string):
    date = extract_digits(input_string)
    try:
        date = datetime.datetime.strptime(date, '%d%m%Y').date()
    except:
        date = None
    
    return date


def validate_passport(input_string):
    passport_pattern = r'\b[A-Z]{2}\d{7}\b'
    passports = re.findall(passport_pattern, input_string)

    if passports:
        return passports[0]
    
    return None


def escape_markdown(text):
    try:
        characters_to_escape = ['_', '*', '[', ']', '`']
        for char in characters_to_escape:
            text = text.replace(char, '\\' + char)
    except:
        pass
    
    return text
    