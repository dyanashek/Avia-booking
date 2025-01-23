from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from core.models import TGUser
from filters import ChatTypeFilter
import config

router = Router()


@router.message(ChatTypeFilter(chat_type='private'), F.video_note)
async def image_to_help_center(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if user:
        try:
            if not user.thread_id:
                topic_name = ''
                sim_card = await sync_to_async(user.sim_cards.first)()
                if sim_card:
                    topic_name += f'{sim_card.sim_phone} '
                topic_name += user.user_id

                new_thread = await message.bot.create_forum_topic(
                    chat_id=config.MESSAGES_CHAT_ID,
                    name=topic_name,
                )
                user.thread_id = new_thread.message_thread_id
                await sync_to_async(user.save)(update_fields=['thread_id'])
        except:
            pass
        
        try:
            await message.bot.send_video_note(
                chat_id=config.MESSAGES_CHAT_ID,
                message_thread_id=user.thread_id,
                video_note=message.video_note.file_id,
            )
        except:
            pass


@router.message(ChatTypeFilter(chat_type=['group', 'supergroup']), F.video_note)
async def image_from_help_center(message: Message, state: FSMContext):
    if message.message_thread_id:
        user = await sync_to_async(TGUser.objects.filter(thread_id=int(message.message_thread_id)).first)()
        if user and config.MESSAGES_CHAT_ID == str(message.chat.id):
            try:
                await message.bot.send_video_note(
                    chat_id=user.user_id,
                    video_note=message.video_note.file_id,
                )
            except:
                pass
