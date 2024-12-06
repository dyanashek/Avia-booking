import os
import uuid

import django

from aiogram import F, Router
from aiogram import types

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from filer.models import Image, Folder

from core.models import TGUser, TGText, Language, Parcel, Flight
from errors.models import AppError

import config
import keyboards
import functions
import utils
from filters import ChatTypeFilter


router = Router()


@router.message(ChatTypeFilter(chat_type='private'), F.photo)
async def handle_photo(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username
    photo = message.photo[-1].file_id

    user = await sync_to_async(TGUser.objects.get)(user_id=user_id)
    if username:
        user.username = username
        await sync_to_async(user.save)()

    user_language = await sync_to_async(lambda: user.language)()
    if not user_language:
        user_language = await sync_to_async(Language.objects.get)(slug='rus')
    curr_input = user.curr_input

    if curr_input and curr_input == 'passport':
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
            counter = 0
            try:
                file_info = await message.bot.get_file(photo)
                downloaded_file = await message.bot.download_file(file_info.file_path)
                
                photo_info = await functions.parse_passport(downloaded_file)
            except Exception as ex:
                counter = config.PARSE_COUNT
                photo_info = [None, None, None, None, None, None, None]

                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='7',
                        main_user=user_id,
                        description=f'Не удалось обработать фото пользователя {user_id}. {ex}',
                    )
                except:
                    pass


            for info in photo_info:
                if info:
                    counter += 1

            if counter >= config.PARSE_COUNT:
                folder, _ = await sync_to_async(Folder.objects.get_or_create)(name="Паспорта")

                if flight:
                    slug = 'flight'
                    pk = flight.pk
                elif parcel:
                    slug = 'parcel'
                    pk = parcel.pk

                try:
                    passport = Image(
                        folder=folder,
                        original_filename=f"{slug}_{pk}.{file_info.file_path.split('.')[-1]}",
                    )
                    await sync_to_async(passport.file.save)(passport.original_filename, downloaded_file)
                    await sync_to_async(passport.save)()
                except Exception as ex:
                    passport = None
                    try:
                        await sync_to_async(AppError.objects.create)(
                            source='1',
                            error_type='7',
                            main_user=user_id,
                            description=f'Не удалось сохранить фото пользователя {user_id}. {ex}',
                        )
                    except:
                        pass


                name, family_name, passport_number, sex, birth_date, start_date, end_date = photo_info

                if flight:
                    flight.passport_photo_flight = passport
                    flight.name = await utils.escape_markdown(name)
                    flight.family_name = await utils.escape_markdown(family_name)
                    flight.passport_number = passport_number
                    flight.sex = sex
                    flight.birth_date = birth_date
                    flight.start_date = start_date
                    flight.end_date = end_date
                    flight.passport_photo_id = photo
                    await sync_to_async(flight.save)()

                elif parcel:
                    parcel.passport_photo_parcel = passport
                    parcel.name = await utils.escape_markdown(name)
                    parcel.family_name = await utils.escape_markdown(family_name)
                    parcel.passport_number = passport_number
                    parcel.sex = sex
                    parcel.birth_date = birth_date
                    parcel.start_date = start_date
                    parcel.end_date = end_date
                    parcel.passport_photo_id = photo
                    await sync_to_async(parcel.save)()
                
                user.curr_input = 'name'
                await sync_to_async(user.save)()

                if name:
                    name_confirm = await sync_to_async(TGText.objects.get)(slug='name_correct_question', language=user_language)
                    reply_text = f'{name_confirm.text} *{name}*?'

                    try:
                        await message.answer(
                                text=reply_text,
                                reply_markup=await keyboards.confirm_or_hand_write_keyboard('name', user_language),
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
                    name_question = await sync_to_async(TGText.objects.get)(slug='name_question', language=user_language)

                    try:
                        await message.answer(
                                text=name_question.text,
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
                wrong_passport = await sync_to_async(TGText.objects.get)(slug='wrong_passport', language=user_language)
                try:
                    await message.answer(
                                    text=wrong_passport.text,
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

    elif curr_input and curr_input == 'user_passport':
        counter = 0
        try:
            file_info = await message.bot.get_file(photo)
            downloaded_file = await message.bot.download_file(file_info.file_path)
            
            photo_info = await functions.parse_passport(downloaded_file)
        except Exception as ex:
            counter = config.PARSE_COUNT
            photo_info = [None, None, None, None, None, None, None]

            try:
                await sync_to_async(AppError.objects.create)(
                    source='1',
                    error_type='7',
                    main_user=user_id,
                    description=f'Не удалось обработать фото пользователя {user_id}. {ex}',
                )
            except:
                pass


        for info in photo_info:
            if info:
                counter += 1

        if counter >= config.PARSE_COUNT:
            folder, _ = await sync_to_async(Folder.objects.get_or_create)(name="Паспорта")

            try:
                passport = Image(
                    folder=folder,
                    original_filename=f"{uuid.uuid4()}_{user.pk}.{file_info.file_path.split('.')[-1]}",
                )
                await sync_to_async(passport.file.save)(passport.original_filename, downloaded_file)
                await sync_to_async(passport.save)()
            except Exception as ex:
                passport = None
                
                try:
                    await sync_to_async(AppError.objects.create)(
                        source='1',
                        error_type='7',
                        main_user=user_id,
                        description=f'Не удалось сохранить фото пользователя {user_id}. {ex}',
                    )
                except:
                    pass

            name, family_name, passport_number, sex, birth_date, start_date, end_date = photo_info

            user.passport_photo_user = passport
            if name:
                user.name = await utils.escape_markdown(name)
            if family_name:
                user.family_name = await utils.escape_markdown(family_name)
            if passport_number:
                user.passport_number = passport_number
            if sex:
                user.sex = sex
            if birth_date:
                user.birth_date = birth_date
            if start_date:
                user.start_date = start_date
            if end_date:
                user.end_date = end_date
            user.passport_photo_id = photo
            user.curr_input = 's-address'
            await sync_to_async(user.save)()

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

        else:
            wrong_passport = await sync_to_async(TGText.objects.get)(slug='wrong_passport', language=user_language)
            try:
                await message.answer(
                                text=wrong_passport.text,
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
