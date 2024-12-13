import os

import django
from aiogram import Router, F
from aiogram.types import CallbackQuery
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from core.models import TGUser, TGText
from errors.models import AppError
from bot.new_keyboards.callbacks import BackCallbackFactory
import keyboards


router = Router()


@router.callback_query(BackCallbackFactory.filter(F.destination == 'menu'))
async def confirm_delivery(callback: CallbackQuery, callback_data: BackCallbackFactory):
    try:
        user, _ = await sync_to_async(TGUser.objects.get_or_create)(user_id=callback.from_user.id)
        user_language = await sync_to_async(lambda: user.language)()
        reply_text = await sync_to_async(TGText.objects.get)(slug='welcome', language=user_language)
        
        await callback.message.edit_text(
            text=reply_text.text,
            reply_markup=await keyboards.flight_or_parcel_keyboard(user_language),
        )
    except:
        try:
            await sync_to_async(AppError.objects.create)(
                source='1',
                error_type='1',
                main_user=str(callback.from_user.id),
                description=f'Не удалось отредактировать сообщение пользователя {callback.from_user.id}.',
            )
        except:
            pass