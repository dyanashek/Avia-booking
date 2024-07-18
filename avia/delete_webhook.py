import asyncio
from aiogram import Bot, Dispatcher

import config


bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher()

# Удаление вебхука
async def delete_webhook():
    await bot.delete_webhook()

asyncio.run(delete_webhook())