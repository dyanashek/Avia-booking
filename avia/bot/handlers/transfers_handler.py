import os

import django
from django.db.models import Q
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from core.models import TGUser
from errors.models import AppError
from money_transfer.models import Delivery
from bot.new_keyboards.callbacks import DeliveryCallbackFactory, DeliveriesCallbackFactory
from bot.new_keyboards import new_keyboards


router = Router()


@router.callback_query(DeliveryCallbackFactory.filter(F.action == 'confirm'))
async def confirm_delivery(callback: CallbackQuery, callback_data: DeliveryCallbackFactory):
    delivery_id = callback_data.delivery_id
    delivery = await sync_to_async(Delivery.objects.filter(id=delivery_id).first)()
    if delivery and delivery.approved_by_client is None:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardBuilder().as_markup(),
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

        delivery.approved_by_client = True
        await sync_to_async(delivery.save)(update_fields=['approved_by_client'])

        reply_text = callback.message.md_text.replace('\\', '').replace('Подтвердите информацию о переводе!', '*Перевод подтвержден!*')
        try:
            await callback.message.edit_text(
                text=reply_text,
                reply_markup=InlineKeyboardBuilder().as_markup(),
                parse_mode='Markdown',
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

    else:
        try:
            await callback.message.edit_text(
                text='Данные устарели!',
                reply_markup=InlineKeyboardBuilder().as_markup(),
                parse_mode='Markdown',
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


@router.callback_query(DeliveryCallbackFactory.filter(F.action == 'cancel'))
async def cancel_delivery(callback: CallbackQuery, callback_data: DeliveryCallbackFactory):
    delivery_id = callback_data.delivery_id
    delivery = await sync_to_async(Delivery.objects.filter(id=delivery_id).first)()
    if delivery and delivery.approved_by_client is None:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardBuilder().as_markup(),
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

        delivery.approved_by_client = False
        await sync_to_async(delivery.save)(update_fields=['approved_by_client'])

        reply_text = callback.message.md_text.replace('\\', '').replace('Подтвердите информацию о переводе!', '*Перевод отменен!*')
        try:
            await callback.message.edit_text(
                text=reply_text,
                reply_markup=InlineKeyboardBuilder().as_markup(),
                parse_mode='Markdown',
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

    else:
        try:
            await callback.message.edit_text(
                text='Данные устарели!',
                reply_markup=InlineKeyboardBuilder().as_markup(),
                parse_mode='Markdown',
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


@router.callback_query(DeliveryCallbackFactory.filter(F.action == 'see'))
async def see_delivery(callback: CallbackQuery, callback_data: DeliveryCallbackFactory, state: FSMContext):
    delivery_id = callback_data.delivery_id
    delivery = await sync_to_async(Delivery.objects.filter(id=delivery_id).first)()
    if delivery:
        delivery_sender = await sync_to_async(lambda: delivery.sender)()
        delivery_user = await sync_to_async(lambda: delivery_sender.user)()

        state_data = await state.get_data()
        delivery_type = state_data.get('delivery_type', 'all')
        page = state_data.get('page', 1)

        if delivery.approved_by_client is True:
            status = await sync_to_async(lambda: delivery.status)()
            if status.slug == 'api':
                reply_message = 'Курьер скоро свяжется с вами!\n\n'
            elif status.slug == 'finished':
                reply_message = 'Деньги получены курьеров!\n\n'
            elif status.slug == 'attempted':
                reply_message = 'Курьеру не удалось связаться с вами!\n\n'

        elif delivery.approved_by_client is False:
            reply_message = 'Перевод отклонен!\n\n'

        elif delivery.approved_by_client is None:
            reply_message = 'Подтвердите информацию о переводе!\n\n'

        reply_message += f'''*Отправление:*\
                    \nНомер отправителя: *{delivery_sender.phone}*\
                    '''
        if delivery.ils_amount:
            reply_message += f'\nСумма в ₪: *{int(delivery.ils_amount)}*'
        
        reply_message += f'''\nСумма в $: *{int(delivery.usd_amount)}*\
                    \nКомиссия в ₪: *{int(delivery.commission)}*\
                    '''

        if delivery.ils_amount:     
            reply_message += f'\nИтого в $: *{int(delivery.total_usd)}*'
        
        reply_message += f'\n\n*Получатели:*'

        transfers = await sync_to_async(lambda: list(delivery.transfers.all()))()
        for num, transfer in enumerate(transfers):
            if transfer.pick_up:
                pick_up = 'да'
            else:
                pick_up = 'нет'

            receiver = await sync_to_async(lambda: transfer.receiver)()
            transfer_message = f'''\n{num + 1}. Код получения: *{transfer.id}*\
                                \nНомер получателя: *{receiver.phone}*\
                                \nСумма: *{int(transfer.usd_amount)} $*\
                                \nДоставка: *{pick_up}*\
                                '''
            
            address = await sync_to_async(lambda: transfer.address)()
            if address:
                transfer_message += f'\nАдрес: *{address.address}*'
            
            if delivery.approved_by_client:
                if transfer.pass_date:
                    date = transfer.pass_date.strftime('%d.%m.%Y') 
                    transfer_message += f'\nВыдано: *{date}*'
                    if transfer.credit:
                        transfer_message += ' (в кредит)'
                else:
                    transfer_message += f'\nВыдано: *нет*'
            transfer_message += '\n'
            reply_message += transfer_message

        try:
            await callback.message.edit_text(
                text=reply_message,
                reply_markup=await new_keyboards.delivery_detail_keyboard(
                    delivery,
                    delivery_type,
                    page,
                ),
                parse_mode='Markdown',
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

    else:
        try:
            await callback.message.edit_text(
                text='Данные устарели!',
                reply_markup=InlineKeyboardBuilder().as_markup(),
                parse_mode='Markdown',
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

@router.callback_query(DeliveriesCallbackFactory.filter(F.delivery_type == 'all'))
async def deliveries_navigation(callback: CallbackQuery, callback_data: DeliveriesCallbackFactory):

    try:
        await callback.message.edit_text(
            text='Выберите тип переводов:',
            reply_markup=await new_keyboards.deliveries_all_keyboard(),
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


@router.callback_query(DeliveriesCallbackFactory.filter())
async def deliveries_types_navigation(callback: CallbackQuery, callback_data: DeliveriesCallbackFactory, state=FSMContext):
    await state.update_data(delivery_type=callback_data.delivery_type)
    await state.update_data(page=callback_data.page)

    if callback_data.delivery_type == 'confirmed':
        reply_text = 'Подтвержденные переводы:'
    else:
        reply_text = 'Отклоненные переводы:'
    
    try:
        user, _ = await sync_to_async(TGUser.objects.get_or_create)(user_id=callback.from_user.id)
        await callback.message.edit_text(
            text=reply_text,
            reply_markup=await new_keyboards.deliveries_keyboard(
                user,
                callback_data.delivery_type,
                callback_data.page,
            ),
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
