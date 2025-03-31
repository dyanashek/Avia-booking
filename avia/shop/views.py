import datetime
import json

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Case, When
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView, TemplateView
from django.utils.translation import gettext as _
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.db import transaction
from django.contrib import messages

from shop.models import (Product, Category, SubCategory, Cart, CartItem, FavoriteProduct, 
                         Order, OrderItem, BuyerProfile, BaseSettings, TopupRequest)
from core.utils import send_message_on_telegram
from .utils import (format_amount, escape_markdown, create_icount_client, send_shop_delivery_address,
                    send_topup_address)


class ProductListView(LoginRequiredMixin,TemplateView):
    template_name = "client/views/catalog/catalog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['popular_products'] = Product.objects.filter(is_popular=True).count()
        context["categories"] = Category.objects.filter(products__isnull=False).distinct()
        context["category"] = self.request.GET.get("category", "all")
        context["subcategory"] = self.request.GET.get("subcategory", '')
        try:
            category_id = int(context['category'])
            context['category'] = Category.objects.get(id=category_id).title
        except:
            pass
        try:
            subcategory_id = int(context['subcategory'])
            context['subcategory'] = SubCategory.objects.get(id=subcategory_id).title
        except:
            pass
        context["subcategories"] = SubCategory.objects.filter(category__title=context['category'], products__isnull=False).select_related('category').distinct()
        return context


class CartListView(LoginRequiredMixin, TemplateView):
    template_name = "client/views/order/cart_k.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if buyer := BuyerProfile.objects.filter(user=self.request.user).first():
            context['address'] = buyer.address
            context['phone'] = buyer.phone
            context['buyer_israel_phone'] = buyer.israel_phone
            context['buyer_israel_address'] = buyer.israel_address
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "client/views/catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category', 'subcategory')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['in_cart'] = Cart.objects.filter(items__product=self.object, user=self.request.user).exists()
        context['in_fav'] = FavoriteProduct.objects.filter(product=self.object, user=self.request.user).exists()
        return context


def get_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategory_options = '<option value="">---------</option>'

    for subcategory in SubCategory.objects.filter(category_id=category_id).distinct():
        subcategory_options += f'<option value="{subcategory.id}">{subcategory.title}</option>'

    return JsonResponse({'subcategories': subcategory_options})


class FavoritesListView(LoginRequiredMixin, ListView):
    template_name = "client/views/profile/favorites.html"
    context_object_name = "favs"
    model = FavoriteProduct
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user).select_related('product')
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        cart_items_ids = [item.product.id for item in cart.items.all()]

        queryset = queryset.annotate(
            in_cart=Case(
                When(product__id__in=cart_items_ids, then=True),
                default=False
            )
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_page'] = int(self.request.GET.get('page', 1)) + 1

        return context


class OrderHistoryView(LoginRequiredMixin, ListView):
    template_name = "client/views/profile/orders.html"
    context_object_name = "orders"
    model = Order
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user).order_by('-created_at').prefetch_related('items', 'items__product')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_page'] = int(self.request.GET.get('page', 1)) + 1

        return context


@login_required
@require_POST
def create_order(request):
    messages.get_messages(request).used = True
    address = request.POST.get('delivery-address')
    phone = request.POST.get('delivery-phone')
    time = request.POST.get('delivery-time')
    date = request.POST.get('delivery-date')

    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    if not cart_items or all(item.product.in_stoplist for item in cart_items):
        return redirect(reverse('shop:cart'))
    
    buyer = BuyerProfile.objects.filter(user=request.user).first()
    if buyer:
        if buyer.balance >= cart.cart_total_sum:
            buyer.balance -= cart.cart_total_sum
        else:
            messages.error(request, 'Недостаточно средств на балансе')
            return redirect(reverse('shop:cart'))
        
        buyer.address = address
        buyer.phone = phone
        buyer.save()

        if not buyer.icount_id:
            icount_id = create_icount_client(buyer, buyer.israel_phone)
            if icount_id:
                buyer.icount_id = icount_id
                buyer.save(update_fields=['icount_id'])
        
    else:
        messages.error(request, 'Пользователь не найден')
        return redirect(reverse('shop:cart'))
    
    order = Order.objects.create(user=request.user,
                                 address=address,
                                 phone=phone,
                                 time=time,
                                 date=date)
    
    order_items = []
    counter = 1
    for item in cart_items:
        if not item.product.in_stoplist:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                item_count=item.item_count
            )

        price = format_amount(item.product.price)
        order_items.append(f'╠{counter}. {escape_markdown(item.product.title)} ({item.item_count} x {price})')
        counter += 1

    cart.items.all().delete()
    if order.total_sum < BaseSettings.objects.first().free_delivery:
        order.delivery_price = BaseSettings.objects.first().delivery_price
        order.save(update_fields=['delivery_price'])

    order_text = '\n'.join(order_items)[:3500]
    order_text = f'╔*Новый заказ №{order.id}:*\n{order_text}'
    order_text += '\n╠═════════════'
    if order.delivery_price > 0:
        order_text += f'\n╠Доставка: {format_amount(order.delivery_price)} ₪'
    order_text += f'\n╚*Итого: {order.readable_total_sum} ₪*'
    delivery_date = datetime.datetime.strptime(order.date, '%Y-%m-%d').strftime('%d.%m.%Y')
    order_text += f'\n\nТелефон: {escape_markdown(order.phone)}\nАдрес: {escape_markdown(order.address)}\nДоставка: {delivery_date} {order.time}'

    base_settings = BaseSettings.objects.first()

    params = {
        'chat_id': base_settings.help_chat,
        'text': order_text,
        'message_thread_id': buyer.thread_id,
        'parse_mode': 'Markdown',
        'reply_markup': json.dumps({
                                'inline_keyboard': [
                                    [{'text': '🚚 Передать в доставку', 'callback_data': f'order:make_delivery:{order.id}'}],
                                    [{'text': '❌ Отменить заказ', 'callback_data': f'order:cancel:{order.id}'}],
                                    [{'text': '⬅️ К заказам пользователя', 'callback_data': 'orders:1'}],
                                    ],
                            })
    }

    send_message_on_telegram(params, base_settings.bot_token)
    
    messages.success(request, 'Заказ успешно создан')
    get_params = request.GET.urlencode()
    return redirect(f'{reverse("shop:orders")}?{get_params}')


@login_required
def repeat_order(request, id):
    order = get_object_or_404(Order, id=id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if not order.items.all() or all(item.product.in_stoplist for item in order.items.all()):
        return redirect(reverse('shop:orders'))

    cart.items.all().delete()
    for item in order.items.all():
        if not item.product.in_stoplist:
            CartItem.objects.create(
                cart=cart,
                product=item.product,
                item_count=item.item_count
            )

    return redirect(reverse('shop:cart'))


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "client/views/profile/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        buyer = BuyerProfile.objects.filter(user=self.request.user).first()
        if buyer:
            context['buyer_phone'] = buyer.phone
            context['buyer_address'] = buyer.address
            context['buyer_balance'] = format_amount(buyer.balance)
            context['buyer_israel_phone'] = buyer.israel_phone
            context['buyer_israel_address'] = buyer.israel_address
            context['buyer_id'] = buyer.tg_id
        return context


@login_required
@require_POST
def change_profile(request):
    address = request.POST.get('address')
    phone = request.POST.get('phone')
    israel_phone = request.POST.get('israel_phone')
    israel_address = request.POST.get('israel_address')
    buyer = BuyerProfile.objects.filter(user=request.user).first()
    if buyer:
        if address:
            buyer.address = address
        if phone:
            buyer.phone = phone
        if israel_phone:
            buyer.israel_phone = israel_phone
        if israel_address:
            buyer.israel_address = israel_address

        buyer.save(update_fields=['address', 'phone', 'israel_phone', 'israel_address'])
        if not buyer.icount_id:
            icount_id = create_icount_client(buyer, israel_phone)
            if icount_id:
                buyer.icount_id = icount_id
                buyer.save(update_fields=['icount_id'])

        messages.success(request, 'Данные успешно обновлены')
    return redirect(reverse('shop:profile'))


def buyer_resend_icount(request, pk):
    buyer = get_object_or_404(BuyerProfile, id=pk)
    
    if not buyer.icount_id:
        icount_id = create_icount_client(buyer, buyer.israel_phone)
        if icount_id:
            buyer.icount_id = icount_id
            buyer.save(update_fields=['icount_id'])

    return redirect('/admin/shop/buyerprofile/')


def order_resend_circuit(request, pk):
    order = get_object_or_404(Order, id=pk)
    if not order.circuit_id:
        stop_id = send_shop_delivery_address(order)
        if stop_id:
            order.circuit_id = stop_id
            order.save(update_fields=['circuit_id'])
    return redirect('/admin/shop/order/')


def topup_resend_circuit(request, pk):
    topup_request = get_object_or_404(TopupRequest, id=pk)
    if not topup_request.circuit_id:
        stop_id = send_topup_address(topup_request)
        if stop_id:
            topup_request.circuit_id = stop_id
            topup_request.save(update_fields=['circuit_id'])
    return redirect('/admin/shop/topuprequest/')


class TopupsView(LoginRequiredMixin, ListView):
    template_name = "client/views/profile/topups.html"
    context_object_name = "topups"
    model = TopupRequest
    paginate_by = 2
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user).order_by('-created_at')
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_page'] = int(self.request.GET.get('page', 1)) + 1
        if buyer := BuyerProfile.objects.filter(user=self.request.user).first():
            context['buyer_balance'] = format_amount(buyer.balance)
            context['buyer_israel_phone'] = buyer.israel_phone
            context['buyer_israel_address'] = buyer.israel_address

        return context


@login_required
@require_POST
def create_topup(request):
    messages.get_messages(request).used = True

    amount = request.POST.get('topup-amount')
    address = request.POST.get('topup-address')
    phone = request.POST.get('topup-phone')
    if amount and address and phone:
        buyer = BuyerProfile.objects.filter(user=request.user).first()
        if buyer:
            try:
                with transaction.atomic():
                    buyer.israel_address = address
                    buyer.israel_phone = phone
                    buyer.save(update_fields=['israel_address', 'israel_phone'])

                    topup = TopupRequest.objects.create(user=request.user,
                                                amount=amount,
                                                address=address,
                                                phone=phone)
                    
                base_settings = BaseSettings.objects.first()

                topup_text = f'*🆕 Новая заявка #{topup.id}:*\n\n'
                topup_text += f'Сумма: *{int(topup.amount)} ₪*'
                topup_text += f'\nАдрес: *{topup.address}*'
                topup_text += f'\nТелефон: *{topup.phone}*'

                params = {
                    'chat_id': base_settings.help_chat,
                    'text': topup_text,
                    'message_thread_id': buyer.thread_id,
                    'parse_mode': 'Markdown',
                    'reply_markup': json.dumps({
                                            'inline_keyboard': [
                                                [{'text': '🚚 Передать в доставку', 'callback_data': f'topup:make_delivery:{topup.id}'}],
                                                [{'text': '✅ Отметить оплаченным', 'callback_data': f'topup:paid:{topup.id}'}],
                                                [{'text': '❌ Отменить пополнение', 'callback_data': f'topup:cancel:{topup.id}'}],
                                                [{'text': '⬅️ К заявкам', 'callback_data': 'topups:1'}],
                                                ],
                                        })
                }

                send_message_on_telegram(params, base_settings.bot_token)

                messages.success(request, 'Заявка на пополнение счета успешно создана')
                return redirect(reverse('shop:topups'))
            except:
                pass


    messages.error(request, 'Ошибка при создании заявки на пополнение счета')
    return redirect(reverse('shop:topups'))
    