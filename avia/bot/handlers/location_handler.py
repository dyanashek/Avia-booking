from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from core.models import TGUser
from filters import ChatTypeFilter
import config

router = Router()


@router.message(ChatTypeFilter(chat_type=['group', 'supergroup']), F.location)
async def image_from_help_center(message: Message, state: FSMContext):
    if message.message_thread_id:
        user = await sync_to_async(TGUser.objects.filter(thread_id=int(message.message_thread_id)).first)()
        if user and config.MESSAGES_CHAT_ID == str(message.chat.id):
            try:
                await message.bot.send_location(
                    chat_id=user.user_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude,
                )
            except:
                pass
