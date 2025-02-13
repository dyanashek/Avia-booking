from django.contrib.auth.decorators import login_required
from django.db.models import Case, When
from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, ListView, TemplateView
from django.utils.translation import gettext as _
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse

from shop.models import Product, Category, SubCategory, Cart, CartItem, FavoriteProduct, Order, OrderItem


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


class CartListView(LoginRequiredMixin,TemplateView):
    template_name = "client/views/order/cart_k.html"


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
def create_order(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    if not cart_items or all(item.product.in_stoplist for item in cart_items):
        return redirect(reverse('shop:cart'))

    order = Order.objects.create(user=request.user)
    for item in cart_items:
        if not item.product.in_stoplist:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                item_count=item.item_count
            )

    cart.items.all().delete()
    return redirect(reverse('shop:orders'))


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
