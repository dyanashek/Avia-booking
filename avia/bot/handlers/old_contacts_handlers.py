import os

import django

from aiogram import F, Router
from aiogram import types

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from core.models import TGUser, TGText, Language, Parcel, Flight
from errors.models import AppError

import keyboards
from filters import ChatTypeFilter


router = Router()


@router.message(ChatTypeFilter(chat_type='private'), F.contact)
async def handle_contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = str(message.from_user.id)
    username = message.from_user.username
    chat_id = message.chat.id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')
    curr_input = user.curr_input

    if curr_input and curr_input == 'phone':
        flight = await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).first)()
        parcel = await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).first)()
        if (flight and parcel) or (not flight and not parcel):
            await sync_to_async(Flight.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            await sync_to_async(Parcel.objects.filter(user=user, complete__isnull=True).update)(complete=False)
            user.curr_input = None
            await sync_to_async(user.save)()

            error = await sync_to_async(TGText.objects.get)(slug='error', language=user_language)
            try:
                await message.answer(
                            text=error,
                            reply_markup=types.ReplyKeyboardRemove(),
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
            user.curr_input = 'address'
            await sync_to_async(user.save)()

            if flight:
                flight.phone = phone
                await sync_to_async(flight.save)()
            elif parcel:
                parcel.phone = phone
                await sync_to_async(parcel.save)()

            question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
            try:
                await message.answer(
                        text=question.text,
                        reply_markup=await keyboards.request_location_keyboard(user_language),
                        parse_mode='Markdown',
                        disable_notification=True,
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
