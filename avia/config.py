import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
MANAGER_ID = os.getenv('MANAGER_ID')
MANAGER_USERNAME = os.getenv('MANAGER_USERNAME')
SIM_MANAGER_ID = os.getenv('SIM_MANAGER_ID')
SIM_MANAGER_USERNAME = os.getenv('SIM_MANAGER_USERNAME')

PARSE_COUNT = 2 # сколько параметров в паспорте алгоритм должен спарсить, чтоб пустить дальше