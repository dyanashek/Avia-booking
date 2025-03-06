import os

import django
from aiogram import Router
from aiogram.types import CallbackQuery
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

import keyboards
from core.models import TGUser, TGText, Language
from errors.models import AppError
from bot.new_keyboards.callbacks import SkipSimPhoneCallbackFactory


router = Router()


@router.callback_query(SkipSimPhoneCallbackFactory.filter())
async def skip_sim(call: CallbackQuery, callback_data: SkipSimPhoneCallbackFactory):
    user_id = call.from_user.id
    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')
    curr_input = user.curr_input

    if curr_input and curr_input == 's-phone':
        user.curr_input = 'sim-fare'
        await sync_to_async(user.save)()

        choose_fare = await sync_to_async(TGText.objects.get)(slug='choose_fare', language=user_language)
        try:
            await call.message.edit_text(
                            text=choose_fare.text,
                            reply_markup=await keyboards.sim_fares_keyboard(),
                            parse_mode='Markdown',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass
    else:
        error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
        try:
            await call.message.edit_text(
                            text=error.text,
                            parse_mode='Markdown',
                            )
        except:
            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='2',
                    main_user=user_id,
                    description=f'Не удалось отправить сообщение пользователю {user_id}.',
                )
            except:
                pass
