import os
import math

import django
from django.db.models import Q
from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from asgiref.sync import sync_to_async
from aiogram.fsm.context import FSMContext

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'avia.settings')
django.setup()

from money_transfer.models import Delivery
from config import TELEGRAM_BOT, PER_PAGE
from bot.new_keyboards.callbacks import (
    DeliveryCallbackFactory,
    DeliveriesCallbackFactory,
    BackCallbackFactory, 
)


async def delivery_action_keyboard(delivery_id):
    keyboard = InlineKeyboardBuilder()

    confirm_btn = InlineKeyboardButton(text='✅', callback_data=DeliveryCallbackFactory(action='confirm', delivery_id=delivery_id).pack())
    cancel_btn = InlineKeyboardButton(text='❌', callback_data=DeliveryCallbackFactory(action='cancel', delivery_id=delivery_id).pack())

    keyboard.row(confirm_btn, cancel_btn)

    return keyboard.as_markup()


async def deliveries_all_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.row(InlineKeyboardButton(text='Подтвержденные ✅', callback_data=DeliveriesCallbackFactory(delivery_type='confirmed').pack()))
    keyboard.row(InlineKeyboardButton(text='В ожидании 🕕', callback_data=DeliveriesCallbackFactory(delivery_type='waiting').pack()))
    keyboard.row(InlineKeyboardButton(text='Отклоненные ❌', callback_data=DeliveriesCallbackFactory(delivery_type='declined').pack()))
    keyboard.row(InlineKeyboardButton(text='⬅️ Назад', callback_data=BackCallbackFactory(destination='menu').pack()))

    return keyboard.as_markup()


async def deliveries_keyboard(user, delivery_type, page=1):
    keyboard = InlineKeyboardBuilder()

    if delivery_type == 'confirmed':
        deliveries = await sync_to_async(lambda: list(Delivery.objects.filter(sender__user=user, approved_by_client=True, status__slug__in=['api', 'finished', 'attempted']).order_by('-created_at').all()))()
    elif delivery_type == 'waiting':
        deliveries = await sync_to_async(lambda: list(Delivery.objects.filter(sender__user=user, approved_by_client__isnull=True, status__slug='waiting').order_by('-created_at').all()))()
    elif delivery_type == 'declined':
        deliveries = await sync_to_async(lambda: list(Delivery.objects.filter(sender__user=user, approved_by_client=False, status__slug='cancelled').order_by('-created_at').all()))()

    if deliveries:
        deliveries_count = len(deliveries)
        pages_count = math.ceil(deliveries_count / PER_PAGE)

        if page > pages_count:
            page = pages_count

        deliveries = deliveries[(page - 1) * PER_PAGE:page * PER_PAGE]
        for num, delivery in enumerate(deliveries):
            delivery_date = delivery.created_at.strftime('%d.%m.%Y')
            total_usd = int(delivery.total_usd )
            keyboard.row(InlineKeyboardButton(text=f'{delivery_date} {total_usd}$', callback_data=DeliveryCallbackFactory(action='see', delivery_id=delivery.id).pack()))

        nav = []
        if pages_count >= 2:
            if page == 1:
                nav.append(InlineKeyboardButton(text=f'<<', callback_data='nothing'))
            else:
                nav.append(InlineKeyboardButton(text=f'<<', callback_data=DeliveriesCallbackFactory(delivery_type=delivery_type, page=page-1).pack()))
            nav.append(InlineKeyboardButton(text=f'{page}/{pages_count}', callback_data=f'nothing'))
            if page == pages_count:
                nav.append(InlineKeyboardButton(text=f'>>', callback_data='nothing'))
            else:
                nav.append(InlineKeyboardButton(text=f'>>', callback_data=DeliveriesCallbackFactory(delivery_type=delivery_type, page=page+1).pack()))
        keyboard.row(*nav)

    back_btn = InlineKeyboardButton(text='⬅️ Назад', callback_data=DeliveriesCallbackFactory(delivery_type='all').pack())
    menu_btn = InlineKeyboardButton(text='🏡 В меню', callback_data=BackCallbackFactory(destination='menu').pack())
    keyboard.row(back_btn)
    keyboard.row(menu_btn)

    return keyboard.as_markup()


async def delivery_detail_keyboard(delivery: Delivery, delivery_type='all', page=1):
    keyboard = InlineKeyboardBuilder()

    status = await sync_to_async(lambda: delivery.status)()

    if status.slug == 'waiting' and delivery.approved_by_client is None:
        confirm_btn = InlineKeyboardButton(text='✅', callback_data=DeliveryCallbackFactory(action='confirm', delivery_id=delivery.id).pack())
        cancel_btn = InlineKeyboardButton(text='❌', callback_data=DeliveryCallbackFactory(action='cancel', delivery_id=delivery.id).pack())
        keyboard.row(confirm_btn, cancel_btn)

    back_btn = InlineKeyboardButton(text='⬅️ Назад', callback_data=DeliveriesCallbackFactory(delivery_type=delivery_type, page=page).pack())
    menu_btn = InlineKeyboardButton(text='🏡 В меню', callback_data=BackCallbackFactory(destination='menu').pack())
    keyboard.row(back_btn)
    keyboard.row(menu_btn)

    return keyboard.as_markup()
