import re
import datetime

from PIL import Image
import pytesseract
import io

import utils


async def parse_passport(passport):
    image = Image.open(passport)
    text = pytesseract.image_to_string(image)

    date_pattern = r'\b\d{2} \d{2} \d{4}\b'
    passport_pattern = r'\b[A-Z]{2}\d{7}\b'
    f_pattern = r'\bF\b'
    m_pattern = r'\bM\b'

    dates = re.findall(date_pattern, text)
    passports = re.findall(passport_pattern, text)
    female = re.findall(f_pattern, text)
    male = re.findall(m_pattern, text)

    name = None
    family_name = None
    passport_number = None
    sex = None
    birth_date = None
    start_date = None
    end_date = None

    info = text.split('\n')

    for num, data in enumerate(info):
        if 'surname' in data.lower():
            counter = num + 1
            while not family_name:
                try:
                    if info[counter]:
                        family_name = info[counter]
                    counter += 1
                except:
                    break
        
        if 'given names' in data.lower():
            counter = num + 1
            while not name:
                try:
                    if info[counter]:
                        name = info[counter]
                    counter += 1
                except:
                    break
    
    if female:
        sex = 'F'
    if male:
        sex = 'M'
    if passports:
        passport_number = passports[0]

    if dates:
        for date in dates:
            date_info = await utils.validate_date(date)
            if date_info:
                if date_info.year < datetime.date.today().year - 10:
                    birth_date = date_info
                elif date_info > datetime.date.today():
                    end_date = date_info
                else:
                    start_date = date_info
    
    return [name, family_name, passport_number, sex, birth_date, start_date, end_date]
    