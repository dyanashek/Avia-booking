from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from core.models import TGUser
from filters import ChatTypeFilter
import config

router = Router()


@router.message(ChatTypeFilter(chat_type=['group', 'supergroup']), F.contact)
async def image_from_help_center(message: Message, state: FSMContext):
    if message.message_thread_id:
        user = await sync_to_async(TGUser.objects.filter(thread_id=int(message.message_thread_id)).first)()
        if user and config.MESSAGES_CHAT_ID == str(message.chat.id):
            try:
                await message.bot.send_contact(
                    chat_id=user.user_id,
                    phone_number=message.contact.phone_number,
                    first_name=message.contact.first_name,
                    last_name=message.contact.last_name,
                    vcard=message.contact.vcard,
                )
            except:
                pass
