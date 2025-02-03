import os

import django

from aiogram import F, Router
from aiogram import types

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from core.models import TGUser, TGText, Language, Parcel, Flight
from errors.models import AppError
from core.utils import get_address

import keyboards
from filters import ChatTypeFilter
import config


router = Router()


@router.message(ChatTypeFilter(chat_type='private'), F.location)
async def handle_location(message: types.Message):
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

    if curr_input and curr_input == 's-address':
        lat = message.location.latitude
        lon = message.location.longitude
        try:
            address = await get_address(lat, lon)
        except:
            address = 'Israel'

        try:
            question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            await message.answer(
                            text=f'{question.text} *{address}*',
                            reply_markup=types.ReplyKeyboardRemove(),
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

        user.lat = lat
        user.lon = lon
        user.addresses = address
        user.curr_input = 's-name'
        await sync_to_async(user.save)()

        if user.name:
            confirm_text = await sync_to_async(TGText.objects.get)(slug='name_correct_question', language=user_language)
            reply_text = f'{confirm_text.text} *{user.name}*?'

            try:
                await message.answer(
                                text=reply_text,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('name', user_language),
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
            question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)
            try:
                await message.answer(
                                text=question.text,
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

    elif curr_input and curr_input == 'sim_collect_money_address':
        lat = message.location.latitude
        lon = message.location.longitude
        try:
            address = await get_address(lat, lon)
        except:
            address = 'Israel'

        try:
            question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            await message.answer(
                            text=f'{question.text} *{address}*',
                            reply_markup=types.ReplyKeyboardRemove(),
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

        user.lat = lat
        user.lon = lon
        user.addresses = address
        user.curr_input = None
        await sync_to_async(user.save)()

        address_question = await sync_to_async(TGText.objects.get)(slug='address_correct_question', language=user_language)
        reply_text = f'{address_question.text}\n*{address}*'

        try:
            await message.answer(
                        text=reply_text,
                        reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('address', user_language),
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
    
    elif curr_input:
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
                                text=error.text,
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
            if curr_input == 'address':
                confirm_application = await sync_to_async(TGText.objects.get)(slug='confirm_application', language=user_language)
                name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                lat = message.location.latitude
                lon = message.location.longitude
                try:
                    location_address = await get_address(lat, lon)
                except:
                    location_address = 'Israel'

                try:
                    question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                    await message.answer(
                                    text=f'{question.text} *{location_address}*',
                                    reply_markup=types.ReplyKeyboardRemove(),
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

                if flight:
                    flight.address = location_address
                    await sync_to_async(flight.save)()

                    route = await sync_to_async(TGText.objects.get)(slug='route', language=user_language)
                    flight_type = await sync_to_async(TGText.objects.get)(slug='type_flight', language=user_language)
                    departure_date = await sync_to_async(TGText.objects.get)(slug='departure', language=user_language)
                    arrival_date = await sync_to_async(TGText.objects.get)(slug='arrival', language=user_language)

                    photo_id = flight.passport_photo_id

                    if flight.type == 'oneway':
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='oneway_button', language=user_language)
                    else:
                        flight_type_text = await sync_to_async(TGText.objects.get)(slug='roundtrip_button', language=user_language)

                    reply_text = f'{confirm_application.text}\n'

                    flight_route_db = await sync_to_async(lambda: flight.route.route)()

                    reply_text += f'\n*{route.text}* {flight_route_db}'
                    reply_text += f'\n*{flight_type.text.lower()}* {flight_type_text}'
                    reply_text += f'\n*{departure_date.text}* {flight.departure_date.strftime("%d.%m.%Y")}'
                    if flight.arrival_date:
                        reply_text += f'\n*{arrival_date.text}* {flight.arrival_date.strftime("%d.%m.%Y")}\n'
                    else:
                        reply_text += '\n'
                    
                    reply_text += f'\n*{name.text}* {flight.name}'
                    reply_text += f'\n*{family_name.text}* {flight.family_name}'
                    reply_text += f'\n*{passport.text}* {flight.passport_number}'
                    reply_text += f'\n*{sex.text}* {flight.sex}'
                    reply_text += f'\n*{birth_date.text}* {flight.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {flight.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {flight.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {flight.phone}'
                    reply_text += f'\n*{address.text}* {flight.address}'

                elif parcel:
                    parcel.address = location_address
                    await sync_to_async(parcel.save)()

                    parcel_type = await sync_to_async(TGText.objects.get)(slug='type_parcel', language=user_language)
                    items_list = await sync_to_async(TGText.objects.get)(slug='contains', language=user_language)
                    fio_receiver = await sync_to_async(TGText.objects.get)(slug='fio_receiver', language=user_language)
                    phone_receiver = await sync_to_async(TGText.objects.get)(slug='receiver_phone', language=user_language)

                    photo_id = parcel.passport_photo_id

                    reply_text = f'{confirm_application.text}\n'

                    parcel_variation_name_db = await sync_to_async(lambda: parcel.variation.name)()

                    reply_text += f'\n*{parcel_type.text}* {parcel_variation_name_db}'
                    reply_text += f'\n*{items_list.text}* {parcel.items_list}'
                    reply_text += f'\n*{fio_receiver.text}* {parcel.fio_receiver}'
                    reply_text += f'\n*{phone_receiver.text}* {parcel.phone_receiver}\n'

                    reply_text += f'\n*{name.text}* {parcel.name}'
                    reply_text += f'\n*{family_name.text}* {parcel.family_name}'
                    reply_text += f'\n*{passport.text}* {parcel.passport_number}'
                    reply_text += f'\n*{sex.text}* {parcel.sex}'
                    reply_text += f'\n*{birth_date.text}* {parcel.birth_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{start_date.text}* {parcel.start_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{end_date.text}* {parcel.end_date.strftime("%d.%m.%Y")}'
                    reply_text += f'\n*{phone.text}* {parcel.phone}'
                    reply_text += f'\n*{address.text}* {parcel.address}'

                user.curr_input = 'confirmation'
                await sync_to_async(user.save)()

                try:
                    await message.answer_photo(
                                caption=reply_text,
                                photo=photo_id,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('confirmation', user_language),
                                parse_mode='Markdown',
                                disable_notification=False,
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
            await message.bot.send_location(
                chat_id=config.MESSAGES_CHAT_ID,
                message_thread_id=user.thread_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
            )
        except:
            pass
