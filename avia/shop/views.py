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

from shop.models import Product, Category, SubCategory, Cart, CartItem, FavoriteProduct, Order, OrderItem, BuyerProfile, BaseSettings
from core.utils import send_message_on_telegram
from .utils import format_amount, escape_markdown


class ProductListView(LoginRequiredMixin,TemplateView):
    template_name = "client/views/catalog/catalog.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['popular_products'] = Product.objects.filter(is_popular=True).count()
        context["categories"] = Category.objects.filter(products__isnull=False).distinct()
        context["category"] = self.request.GET.get("category", "all")
        context["subcategory"] = self.request.GET.get("subcategory", '')
        context["subcategories"] = SubCategory.objects.filter(category__title=context['category'], products__isnull=False).select_related('category').distinct()
        return context


class CartListView(LoginRequiredMixin, TemplateView):
    template_name = "client/views/order/cart_k.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if buyer := BuyerProfile.objects.filter(user=self.request.user).first():
            context['address'] = buyer.address
            context['phone'] = buyer.phone
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
    address = request.POST.get('delivery-address')
    phone = request.POST.get('delivery-phone')
    time = request.POST.get('delivery-time')
    date = request.POST.get('delivery-date')

    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    if not cart_items or all(item.product.in_stoplist for item in cart_items):
        return redirect(reverse('shop:cart'))

    order = Order.objects.create(user=request.user,
                                 address=address,
                                 phone=phone,
                                 time=time,
                                 date=date)
    
    buyer = BuyerProfile.objects.filter(user=request.user).first()
    if buyer:
        buyer.address = address
        buyer.phone = phone
        buyer.save()

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

    order_text = '\n'.join(order_items)[:3500]
    order_text = f'╔*Новый заказ №{order.id}:*\n{order_text}'
    order_text += '\n╠═════════════'
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
                                    [{'text': '💳 Пометить оплаченным', 'callback_data': f'order:pay:{order.id}'},
                                    {'text': '🚚 Передать в доставку', 'callback_data': f'order:make_delivery:{order.id}'},
                                    {'text': '❌ Отменить заказ', 'callback_data': f'order:cancel:{order.id}'},
                                    {'text': '⬅️ К заказам пользователя', 'callback_data': 'orders:1'},
                                    ],
                                ]
                            })
    }

    send_message_on_telegram(params, base_settings.bot_token)
    
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
