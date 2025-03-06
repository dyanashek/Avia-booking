import os
import datetime

import django

from aiogram import F, Router
from aiogram import types
from aiogram.fsm.context import FSMContext

from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()


from core.models import (TGUser, TGText, Language, Parcel, Flight, UserMessage, Notification,)
from errors.models import AppError

import config
import keyboards
import utils
from bot.new_keyboards import new_keyboards
from filters import ChatTypeFilter


router = Router()


@router.message(ChatTypeFilter(chat_type='private'), F.text)
async def handle_text(message: types.Message, state: FSMContext):
    """Handles message with type text."""

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
    input_info = await utils.escape_markdown(message.text)

    if curr_input and 'flightprice' in curr_input and user_id == config.MANAGER_ID:
        data = curr_input.split('_')
        flight_id = int(data[1])
        price = round(await utils.validate_price(input_info), 2)

        if price:
            try:
                await message.answer(
                            text=f'Стоимость *{price} ₪*?',
                            reply_markup=await keyboards.confirm_price_keyboard('flight', flight_id, price),
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
            try:
                await message.answer(
                                text='Не похоже на корректную стоимость, введите еще раз стоимость в шекелях.',
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

    elif curr_input and 'parcelprice' in curr_input and user_id == config.MANAGER_ID:
        data = curr_input.split('_')
        parcel_id = int(data[1])
        price = await utils.validate_price(input_info)

        if price:
            try:
                await message.answer(
                                text=f'Стоимость *{price} ₪*?',
                                reply_markup=await keyboards.confirm_price_keyboard('parcel', parcel_id, price),
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
            try:
                await message.answer(
                                text='Не похоже на корректную стоимость, введите еще раз стоимость в шекелях.',
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

    elif curr_input and 'manager-sim' in curr_input and user_id == config.SIM_MANAGER_ID:
        data = curr_input.split('_')
        sim_user_id = int(data[1])
        fare_id = int(data[2])
        phone = await utils.validate_phone_sim(input_info)
        if phone:
            user.curr_input = f'manager-sim_{phone}'
            await sync_to_async(user.save)()

            try:
                await message.answer(
                                text=f'Номер телефона выдаваемой симки: *{phone}*?',
                                reply_markup=await keyboards.sim_confirm_phone_keyboard(sim_user_id, fare_id),
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
            try:
                await message.answer(
                                text='Не похоже на корректный номер телефона, введите еще раз (должен начинаться с 972).',
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

    elif curr_input and curr_input == 's-address':
        user.addresses = input_info 
        user.curr_input = 's-name'
        await sync_to_async(user.save)()

        if user.name:
            confirm_text = await sync_to_async(TGText.objects.get)(slug='name_correct_question', language=user_language)
            reply_text = f'{confirm_text.text} *{user.name}*?'

            try:
                question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                await message.answer(
                                text=f'{question.text} *{input_info}*',
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
    
    elif curr_input and curr_input == 's-name':
        user.name = input_info 
        user.curr_input = 's-familyname'
        await sync_to_async(user.save)()

        if user.family_name:
            confirm_text = await sync_to_async(TGText.objects.get)(slug='familyname_correct_question', language=user_language)
            reply_text = f'{confirm_text.text} *{user.family_name}*?'

            try:
                await message.answer(
                                text=reply_text,
                                reply_markup=await keyboards.sim_confirm_or_hand_write_keyboard('familyname', user_language),
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
            question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)
            try:
                await message.answer(
                                text=question.text,
                                parse_mode='Markdown',
                                )
            except:
                pass

    elif curr_input and curr_input == 's-familyname':
        user.family_name = input_info 
        user.curr_input = 's-phone'
        await sync_to_async(user.save)()

        question = await sync_to_async(TGText.objects.get)(slug='sim_phone_question', language=user_language)
        try:
            await message.answer(
                            text=question.text,
                            reply_markup=await new_keyboards.skip_sim_phone_keyboard(user_language),
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
    
    elif curr_input and curr_input == 's-phone':
        is_phone_valid = await utils.validate_phone(input_info)
        if is_phone_valid:
            await state.update_data(phone=input_info)
            user.curr_input = 'sim-fare'
            await sync_to_async(user.save)()

            choose_fare = await sync_to_async(TGText.objects.get)(slug='choose_fare', language=user_language)
            try:
                await message.answer(
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
            error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
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

    elif curr_input and curr_input == 'sim_collect_money_address':
        user.curr_input = None
        user.addresses = input_info
        await sync_to_async(user.save)()

        address_question = await sync_to_async(TGText.objects.get)(slug='address_correct_question', language=user_language)
        reply_text = f'{address_question.text}\n*{input_info}*'

        try:
            question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
            await message.answer(
                            text=f'{question.text} *{input_info}*',
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

    elif curr_input and curr_input == 'sim-payment-date':
        sim_card = await sync_to_async(user.sim_cards.first)()

        if sim_card and not sim_card.ready_to_pay:
            payment_date = await utils.validate_date(input_info)
            if (payment_date and (payment_date <= (datetime.datetime.utcnow() + datetime.timedelta(hours=3) + datetime.timedelta(days=31)).date()) and
            payment_date > (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()):
                if sim_card.next_payment <= payment_date:
                    fare_price = await sync_to_async(lambda: sim_card.fare.price)()
                    debt = sim_card.debt + fare_price
                else:
                    debt = sim_card.debt
                
                sim_card.pay_date = payment_date
                sim_card.notified = False
                await sync_to_async(sim_card.save)()

                user.curr_input = None
                await sync_to_async(user.save)()

                pay_date_text = await sync_to_async(TGText.objects.get)(slug='pay_date', language=user_language)
                sim_debt = await sync_to_async(TGText.objects.get)(slug='sim_debt_future', language=user_language)
                human_pay_date = sim_card.pay_date.strftime('%d.%m.%Y')
                reply_text = f'''
                        *{sim_card.sim_phone}*\
                        \n{sim_debt.text}:\
                        \n*{debt} ₪*\
                        \n{pay_date_text.text} *{human_pay_date}*\
                        '''

                try:
                    await message.answer(
                                    text=reply_text,
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
                error = await sync_to_async(TGText.objects.get)(slug='sim_payment_date_error', language=user_language)
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
            if curr_input == 'name':
                if flight:
                    flight.name = input_info
                    family_name = flight.family_name
                    await sync_to_async(flight.save)()
                elif parcel:
                    parcel.name = input_info
                    family_name = parcel.family_name
                    await sync_to_async(parcel.save)()
                
                user.curr_input = 'familyname'
                await sync_to_async(user.save)()

                if family_name:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='familyname_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{family_name}*?'

                    try:
                        await message.answer(
                                        text=reply_text,
                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('familyname', user_language),
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
                    question = await sync_to_async(TGText.objects.get)(slug='familyname_question', language=user_language)

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

            elif curr_input == 'familyname':
                if flight:
                    flight.family_name = input_info
                    passport_num = flight.passport_number
                    await sync_to_async(flight.save)()
                elif parcel:
                    parcel.family_name = input_info
                    passport_num = parcel.passport_number
                    await sync_to_async(parcel.save)()
                
                user.curr_input = 'passportnum'
                await sync_to_async(user.save)()

                if passport_num:
                    confirm_text = await sync_to_async(TGText.objects.get)(slug='passport_correct_question', language=user_language)
                    reply_text = f'{confirm_text.text} *{passport_num}*?'

                    try:
                        await message.answer(
                                        text=reply_text,
                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('passportnum', user_language),
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
                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)

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

            elif curr_input == 'passportnum':
                passport_num = await utils.validate_passport(input_info)
                if passport_num:
                    if flight:
                        flight.passport_number = passport_num
                        await sync_to_async(flight.save)()
                        sex = flight.sex
                    elif parcel:
                        parcel.passport_number = passport_num
                        await sync_to_async(parcel.save)()
                        sex = parcel.sex
                    
                    user.curr_input = 'sex'
                    await sync_to_async(user.save)()

                    if sex:
                        confirm_text = await sync_to_async(TGText.objects.get)(slug='sex_correct_question', language=user_language)
                        reply_text = f'{confirm_text.text} *{sex}*?'

                        try:
                            await message.answer(
                                            text=reply_text,
                                            reply_markup=await keyboards.confirm_or_hand_write_keyboard('sex', user_language),
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
                        question = await sync_to_async(TGText.objects.get)(slug='sex_question', language=user_language)

                        try:
                            await message.answer(
                                    text=question.text,
                                    reply_markup=await keyboards.sex_keyboard(user_language),
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
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='passport_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await message.answer(
                                text=reply_text,
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

            elif curr_input == 'birthdate':
                birth_date = await utils.validate_date(input_info)
                if birth_date:
                    if flight:
                        flight.birth_date = birth_date
                        await sync_to_async(flight.save)()
                        start_date = flight.start_date
                    elif parcel:
                        parcel.birth_date = birth_date
                        await sync_to_async(parcel.save)()
                        start_date = parcel.start_date
                    
                    user.curr_input = 'startdate'
                    await sync_to_async(user.save)()

                    if start_date:
                        start_date = start_date.strftime('%d.%m.%Y')

                        confirm_text = await sync_to_async(TGText.objects.get)(slug='start_correct_question', language=user_language)
                        reply_text = f'{confirm_text.text} *{start_date}*?'

                        try:
                            await message.answer(
                                        text=reply_text,
                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('startdate', user_language),
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
                        question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)

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

                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='birth_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await message.answer(
                                text=reply_text,
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

            elif curr_input == 'startdate':
                start_date = await utils.validate_date(input_info)
                if start_date:
                    if flight:
                        flight.start_date = start_date
                        await sync_to_async(flight.save)()
                        end_date = flight.end_date
                    elif parcel:
                        parcel.start_date = start_date
                        await sync_to_async(parcel.save)()
                        end_date = parcel.end_date
                    
                    user.curr_input = 'enddate'
                    await sync_to_async(user.save)()

                    if end_date:
                        end_date = end_date.strftime('%d.%m.%Y')

                        confirm_text = await sync_to_async(TGText.objects.get)(slug='end_correct_question', language=user_language)
                        reply_text = f'{confirm_text.text} *{end_date}*?'

                        try:
                            await message.answer(
                                        text=reply_text,
                                        reply_markup=await keyboards.confirm_or_hand_write_keyboard('enddate', user_language),
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
                        question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)

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
                
                else:
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='start_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await message.answer(
                                text=reply_text,
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

            elif curr_input == 'enddate':
                end_date = await utils.validate_date(input_info)
                if end_date:
                    if flight:
                        flight.end_date = end_date
                        await sync_to_async(flight.save)()
                    elif parcel:
                        parcel.end_date = end_date
                        await sync_to_async(parcel.save)()
                    
                    user.curr_input = 'phone'
                    await sync_to_async(user.save)()

                    phone_question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)

                    try:
                        await message.answer(
                                text=phone_question.text,
                                parse_mode='Markdown',
                                reply_markup=await keyboards.request_phone_keyboard(user_language),
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
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='end_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await message.answer(
                                text=reply_text,
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

            elif curr_input == 'phone':
                phone = await utils.validate_phone(input_info)
                if phone:
                    if flight:
                        flight.phone = phone
                        await sync_to_async(flight.save)()
                    elif parcel:
                        parcel.phone = phone
                        await sync_to_async(parcel.save)()

                    user.curr_input = 'address'
                    await sync_to_async(user.save)()

                    question = await sync_to_async(TGText.objects.get)(slug='address_question', language=user_language)
                    try:
                        await message.answer(
                                text=question.text,
                                reply_markup=await keyboards.request_location_keyboard(user_language),
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
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='phone_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await message.answer(
                                text=reply_text,
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

            elif curr_input == 'address':
                try:
                    question = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)
                    await message.answer(
                                    text=f'{question.text} *{input_info}*',
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

                if flight:
                    flight.address = input_info
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
                    parcel.address = input_info
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
        
            elif parcel and curr_input == 'fio_receiver':
                parcel.fio_receiver = input_info
                await sync_to_async(parcel.save)()

                user.curr_input = 'contains'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='contains_question', language=user_language)
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
            
            elif parcel and curr_input == 'contains':
                parcel.items_list = input_info
                await sync_to_async(parcel.save)()

                user.curr_input = 'phone_receiver'
                await sync_to_async(user.save)()

                question = await sync_to_async(TGText.objects.get)(slug='phone_receiver_question', language=user_language)

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

            elif parcel and curr_input == 'phone_receiver':
                phone_receiver = await utils.validate_phone(input_info)
                if phone_receiver:
                    parcel.phone_receiver = phone_receiver
                    await sync_to_async(parcel.save)()

                    user.curr_input = 'passport'
                    await sync_to_async(user.save)()

                    if user.name and user.family_name and user.sex and user.birth_date and user.start_date and\
                    user.end_date and user.passport_number and user.passport_photo_id and user.phone and user.addresses:
                        reuse = await sync_to_async(TGText.objects.get)(slug='reuse', language=user_language)
                        name = await sync_to_async(TGText.objects.get)(slug='name', language=user_language)
                        family_name = await sync_to_async(TGText.objects.get)(slug='familyname', language=user_language)
                        passport = await sync_to_async(TGText.objects.get)(slug='passport', language=user_language)
                        sex = await sync_to_async(TGText.objects.get)(slug='sex', language=user_language)
                        birth_date = await sync_to_async(TGText.objects.get)(slug='birth', language=user_language)
                        start_date = await sync_to_async(TGText.objects.get)(slug='start', language=user_language)
                        end_date = await sync_to_async(TGText.objects.get)(slug='end', language=user_language)
                        phone = await sync_to_async(TGText.objects.get)(slug='phone', language=user_language)
                        address = await sync_to_async(TGText.objects.get)(slug='address', language=user_language)

                        reply_text = f'{reuse.text}\n'
                        
                        reply_text += f'\n*{name.text}* {user.name}'
                        reply_text += f'\n*{family_name.text}* {user.family_name}'
                        reply_text += f'\n*{passport.text}* {user.passport_number}'
                        reply_text += f'\n*{sex.text}* {user.sex}'
                        reply_text += f'\n*{birth_date.text}* {user.birth_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{start_date.text}* {user.start_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{end_date.text}* {user.end_date.strftime("%d.%m.%Y")}'
                        reply_text += f'\n*{phone.text}* {user.phone}'
                        reply_text += f'\n*{address.text}* {user.addresses}'

                        try:
                            await message.answer_photo(
                                    caption=reply_text,
                                    photo=user.passport_photo_id,
                                    reply_markup=await keyboards.confirm_or_hand_write_keyboard('passport', user_language),
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
                        passport_request = await sync_to_async(TGText.objects.get)(slug='passport_photo_question', language=user_language)

                        try:
                            await message.answer(
                                    text=passport_request.text,
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
                    error = await sync_to_async(TGText.objects.get)(slug='not_valid', language=user_language)
                    question = await sync_to_async(TGText.objects.get)(slug='phone_receiver_question', language=user_language)
                    reply_text = f'{error.text}\n{question.text}'

                    try:
                        await message.answer(
                                text=reply_text,
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
        
        await sync_to_async(UserMessage.objects.create)(
            user=user,
            message=input_info,
        )


@router.message(ChatTypeFilter(chat_type=['group', 'supergroup']), F.text)
async def handle_text(message):
    reply_text = message.text
    if message.reply_to_message and str(message.chat.id) == config.MESSAGES_CHAT_ID:
        text = message.reply_to_message.text

        if 'TG id: ' in text:
            tg_id = await utils.extract_tg_id(text)

            if tg_id:
                user = await sync_to_async(TGUser.objects.filter(user_id=tg_id).first)()
                if user:
                    await sync_to_async(Notification.objects.create)(
                                user=user,
                                text=reply_text,
                            )
