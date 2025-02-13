import json
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, When, Q
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin

from api.serializers import ProductSerializer, CartSerializer, OrderSerializer
from shop.models import Category, SubCategory, Product, FavoriteProduct, Cart, CartItem, Order, OrderItem


@method_decorator(login_required, name='get')
class ProductsView(View):
    def get(self, request, *args, **kwargs):
        fav_products_ids = [fav.product.id for fav in FavoriteProduct.objects.filter(user=request.user).all()]
        products = Product.objects.filter(in_stoplist=False).annotate(
            in_fav=Case(
                When(id__in=fav_products_ids, then=True),
                default=False,
            )
        )

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items_ids = [item.product.id for item in cart.items.all()]
        products = products.annotate(
            in_cart=Case(
                When(id__in=cart_items_ids, then=True),
                default=False
            )
        )

        category_title = request.GET.get("category")
        category = Category.objects.filter(title=category_title).first()
        subcategory_title = request.GET.get("subcategory")
        subcategory = SubCategory.objects.filter(title=subcategory_title).first()
        search_query = request.GET.get("search")

        if category:
            products = products.filter(category__title=category)
        if category_title == 'popular':
            products = products.filter(is_popular=True)
        if subcategory:
            products = products.filter(subcategory__title=subcategory)
        if search_query:
            products = products.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query)).distinct()

        count = int(request.GET.get("count", 0))
        products = products[count:count + 12]                    
        serializer = ProductSerializer(products, many=True)
        return JsonResponse({"products": serializer.data}, status=200)


@method_decorator(login_required, name='get')
class CartQuantityView(View):
    def get(self, request, *args, **kwargs):
        items_quantity = CartItem.objects.filter(cart__user=request.user).count()
        return JsonResponse({"items_num": items_quantity}, status=200)
    

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class ChangeFavoritesView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            json_data = json.loads(request.body.decode("utf-8"))
            product_id = json_data.get("product_id")
            if not product_id:
                return JsonResponse({"Error": "Блюдо не найдено"}, status=400)
            product = Product.objects.filter(id=product_id).first()
            if not product:
                return JsonResponse({"Error": "Блюдо не найдено"}, status=404)
            favorite = FavoriteProduct.objects.filter(product=product, user=request.user).first()
            if favorite:
                favorite.delete()
                message = 'deleted'
            else:
                FavoriteProduct.objects.create(product=product, user=request.user)
                message = 'added'
            return JsonResponse({"Message": message}, status=200)
        except Exception as e:
            return JsonResponse({"Error": f"{e}"}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class AddToCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            product_id = data.get("product_id")

            if product_id is None:
                return JsonResponse({"Error": "Ошибка при добавлении товара в корзину"}, status=400)
            product = Product.objects.filter(id=product_id, in_stoplist=False).first()
            if not product:
                return JsonResponse({"Error": "Ошибка при добавлении товара в корзину"}, status=400)
            
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item = CartItem.objects.filter(product=product, cart=cart).first()
            if cart_item:
                cart_item.item_count += 1
                cart_item.save()
            else:
                CartItem.objects.create(product=product, cart=cart)
            return JsonResponse({"Message": "ok"}, status=200)
        
        except Exception as e:
            return JsonResponse({"Error": f"{e}"}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class DecreaseFromCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            product_id = data.get("product_id")

            if product_id is None:
                return JsonResponse({"Error": "Ошибка при удалении товара из корзины"}, status=400)
            product = Product.objects.filter(id=product_id, in_stoplist=False).first()
            if not product:
                return JsonResponse({"Error": "Ошибка при удалении товара из корзины"}, status=400)
            
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item = CartItem.objects.filter(product=product, cart=cart).first()
            if cart_item and cart_item.item_count > 1:
                cart_item.item_count -= 1
                cart_item.save()
            elif cart_item:
                cart_item.delete()
            return JsonResponse({"Message": "ok"}, status=200)
        
        except Exception as e:
            return JsonResponse({"Error": f"{e}"}, status=500)
        

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class DeleteFromCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            product_id = data.get("product_id")

            if product_id is None:
                return JsonResponse({"Error": "Ошибка при удалении товара из корзины"}, status=400)
            product = Product.objects.filter(id=product_id, in_stoplist=False).first()
            if not product:
                return JsonResponse({"Error": "Ошибка при удалении товара из корзины"}, status=400)
            
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_item = CartItem.objects.filter(product=product, cart=cart).first()
            if cart_item:
                cart_item.delete()
            return JsonResponse({"Message": "ok"}, status=200)
        
        except Exception as e:
            return JsonResponse({"Error": f"{e}"}, status=500)
        

@method_decorator(login_required, name='get')
class CartView(View):
    def get(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        cart_info = {"cart": serializer.data}
        return JsonResponse(cart_info, status=200)


@method_decorator(login_required, name='get')
class OrderDetailView(View):
    def get(self, request, *args, **kwargs):
        order = Order.objects.filter(id=kwargs.get("pk")).first()
        if not order:
            return JsonResponse({"Error": "Заказ не найден"}, status=404)
        order_serializer = OrderSerializer(order)
        return JsonResponse({"order": order_serializer.data}, status=200)
    