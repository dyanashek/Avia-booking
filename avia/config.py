import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
MANAGER_ID = os.getenv('MANAGER_ID')
MANAGER_USERNAME = os.getenv('MANAGER_USERNAME')

PARSE_COUNT = 2