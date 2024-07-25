import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_DRIVERS_TOKEN = os.getenv('TELEGRAM_DRIVERS_TOKEN')
TELEGRAM_SIM_TOKEN = os.getenv('TELEGRAM_SIM_TOKEN')
MANAGER_ID = os.getenv('MANAGER_ID')
MANAGER_USERNAME = os.getenv('MANAGER_USERNAME')
SIM_MANAGER_ID = os.getenv('SIM_MANAGER_ID')
SIM_MANAGER_USERNAME = os.getenv('SIM_MANAGER_USERNAME')

ICOUNT_COMPANY_ID = os.getenv('ICOUNT_COMPANY_ID')
ICOUNT_USERNAME = os.getenv('ICOUNT_USERNAME')
ICOUNT_PASSWORD = os.getenv('ICOUNT_PASSWORD')

OLD_ICOUNT_COMPANY_ID = os.getenv('OLD_ICOUNT_COMPANY_ID')
OLD_ICOUNT_USERNAME = os.getenv('OLD_ICOUNT_USERNAME')
OLD_ICOUNT_PASSWORD = os.getenv('OLD_ICOUNT_PASSWORD')

PARSE_COUNT = 2 # сколько параметров в паспорте алгоритм должен спарсить, чтоб пустить дальше

ICOUNT_CREATE_USER_ENDPOINT = 'https://api.icount.co.il/api/v3.php/client/create'
ICOUNT_CREATE_INVOICE_ENDPOINT = 'https://api.icount.co.il/api/v3.php/doc/create'