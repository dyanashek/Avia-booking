import os

import django
from django.db import transaction

import asyncio
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from core.models import UsersSim, TGUser, SimFare, OldSim

import config
import text
import utils


bot = Bot(token=config.TELEGRAM_SIM_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start_message(message: types.Message):
    user_id = str(message.from_user.id)
    user = await sync_to_async(TGUser.objects.filter(user_id=user_id).first)()
    if user:
        sim_card = await sync_to_async(user.sim_cards.all().first)()
        if sim_card:
            await bot.send_message(chat_id=user_id,
                            text=text.ALREADY_HAVE_SIM,
                            )
        else:
            await bot.send_message(chat_id=user_id,
                            text=text.SIM_PHONE,
                            )
    else:
        user = await sync_to_async(OldSim.objects.filter(user_id=user_id, to_main_bot=True).first)()
        if is_exists:
            await bot.send_message(chat_id=user_id,
                            text=text.ALREADY_HAVE_SIM,
                            )
        else:
            await bot.send_message(chat_id=user_id,
                            text=text.SIM_PHONE,
                            )

@dp.message(F.text)
async def handle_text(message):
    """Handles message with type text."""

    user_id = str(message.from_user.id)
    username = message.from_user.username

    input_info = await utils.escape_markdown(message.text)

    phone = await utils.validate_phone_sim(input_info)

    if phone:
        old_sim = await sync_to_async(OldSim.objects.filter(sim_phone=phone).first)()
        if old_sim:
            if old_sim.to_main_bot:
                if old_sim.user_id == user_id:
                    await bot.send_message(chat_id=user_id,
                                text=text.REGISTERED_ALREADY,
                                )
                else:
                    await bot.send_message(chat_id=user_id,
                                text=text.PHONE_ALREADY_USED,
                                )
            else:
                user = await sync_to_async(TGUser.objects.filter(user_id=user_id).first)()
                try:
                    sim_card = await sync_to_async(user.sim_cards.all().first)()
                except:
                    sim_card = None

                if sim_card:
                    await bot.send_message(chat_id=user_id,
                            text=text.ALREADY_HAVE_SIM,
                            )
                
                else:
                    user, created = await sync_to_async(TGUser.objects.get_or_create)(
                        user_id=user_id,
                    )
                    if created:
                        user.name = old_sim.name
                        user.addresses = old_sim.address
                        user.username = username
                        user.active = False
                        await sync_to_async(user.save)()
                    

                    try:
                        fare = await sync_to_async(lambda: old_sim.fare)()

                        await sync_to_async(UsersSim.objects.create)(
                            user=user,
                            fare=fare,
                            sim_phone=old_sim.sim_phone,
                            next_payment=old_sim.next_payment,
                            debt=old_sim.debt,
                            icount_id=old_sim.icount_id,
                            is_old_sim=True,
                        )
                        old_sim.user_id = user_id
                        old_sim.to_main_bot = True
                        await sync_to_async(old_sim.save)()
                        
                        await bot.send_message(chat_id=user_id,
                            text=text.SUCCESS,
                            parse_mode='Markdown',
                            )
                    except:
                        await bot.send_message(chat_id=user_id,
                        text=text.TRY_AGAIN,
                        )

        else:
            await bot.send_message(chat_id=user_id,
                                    text=text.WRONG_PHONE,
                                    )
    else:
        await bot.send_message(chat_id=user_id,
                        text=text.WRONG_TYPE,
                        )
                

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())