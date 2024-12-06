import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import Redis, RedisStorage
from aiogram.types import BotCommand

import config
from bot.handlers import (
    old_commands_handlers,
    old_contacts_handlers,
    old_location_handlers,
    old_photo_handlers,
    old_query_handlers,
    old_text_handlers,
)


async def main() -> None:
    redis = Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        decode_responses=True,
    )

    storage = RedisStorage(redis=redis, state_ttl=3600 * 24)

    bot = Bot(token=config.TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)

    dp.include_router(old_commands_handlers.router)
    dp.include_router(old_query_handlers.router)
    dp.include_router(old_text_handlers.router)
    dp.include_router(old_contacts_handlers.router)
    dp.include_router(old_photo_handlers.router)
    dp.include_router(old_location_handlers.router)

    cmds = [
        BotCommand(command="start", description="Меню"),
        BotCommand(command="language", description="Выбрать язык"),
        BotCommand(command="getid", description="Узнать id"),
    ]
    await bot.set_my_commands(cmds)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
