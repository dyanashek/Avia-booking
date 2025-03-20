import json
import urllib.parse

from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, When, Q, Count, Subquery, OuterRef
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib.auth import get_user_model, login
from django.urls import reverse

from api.serializers import ProductSerializer, CartSerializer, OrderSerializer, FavoriteProductSerializer
from shop.models import Category, SubCategory, Product, FavoriteProduct, Cart, CartItem, Order, OrderItem
from api.utils import validate_web_app_data


@method_decorator(login_required, name='dispatch')
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
        products = products.annotate(
            item_count=Subquery(
                CartItem.objects.filter(product=OuterRef('pk'), cart__user=request.user).values('item_count')[:1]
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
        all = request.GET.get("all")
        if all:
            products = products[:count]                    
        else:
            products = products[count:count + 12]
        serializer = ProductSerializer(products, many=True)
        return JsonResponse({"products": serializer.data}, status=200)


@method_decorator(login_required, name='dispatch')
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
        

@method_decorator(login_required, name='dispatch')
class CartView(View):
    def get(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        cart_info = {"cart": serializer.data}
        return JsonResponse(cart_info, status=200)


@method_decorator(login_required, name='dispatch')
class OrderDetailView(View):
    def get(self, request, *args, **kwargs):
        order = Order.objects.filter(id=kwargs.get("pk")).first()
        if not order:
            return JsonResponse({"Error": "Заказ не найден"}, status=404)
        order_serializer = OrderSerializer(order)
        return JsonResponse({"order": order_serializer.data}, status=200)


@method_decorator(login_required, name='dispatch')
class FavoritesView(View):
    def get(self, request, *args, **kwargs):
        favs = FavoriteProduct.objects.filter(user=request.user).select_related('product')
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items_ids = [item.product.id for item in cart.items.all()]
        favs = favs.annotate(
            in_cart=Case(
                When(product__id__in=cart_items_ids, then=True),
                default=False
            )
        )
        favs = favs.annotate(
            item_count=Subquery(
                CartItem.objects.filter(product=OuterRef('product__pk'), cart__user=request.user).values('item_count')[:1]
            )
        )
        count = int(request.GET.get("count", 0))
        all = request.GET.get("all")
        if all:
            favs = favs[:count]                    
        else:
            favs = favs[count:count + 12]
        serializer = FavoriteProductSerializer(favs, many=True)
        return JsonResponse({"favorites": serializer.data}, status=200)


@require_POST
@csrf_exempt
def verify_user(request):
    """Верификация и авторизация пользователя web-app"""
    user_tg_id = request.POST.get('tg_id')
    if user_tg_id:
        user = get_user_model().objects.filter(username=f'shop{user_tg_id}').first()
        if user:
            try:
                login(request, user)
            except:
                pass
            return JsonResponse({"success": True})
    
    return JsonResponse({"success": False})

    # try:
    #     body = json.loads(request.body)
    #     init_data = str(body.get('initData'))
    #     init_data = urllib.parse.unquote(init_data)
    #     if validate_web_app_data(init_data):
    #         init_data = urllib.parse.parse_qs(init_data)
    #         init_data = {key: value[0] for key, value in init_data.items() if key == 'user'}
    #         init_data['user'] = json.loads(init_data['user'])

    #         init_data = init_data.get('user')
    #         tg_id=init_data.get('id')
    #         user = get_user_model().objects.filter(username=f'shop{tg_id}').first()
    #         if user:
    #             try:
    #                 login(request, user)
    #             except:
    #                 pass
    #             if request.GET.get('product'):
    #                 return redirect('shop:product_detail', pk=request.GET.get('product'))
    #             get_params = request.GET.urlencode()
    #             return redirect(f'{reverse("shop:orders")}?{get_params}')
    #         else:
    #             return redirect('shop:error')
    # except:
    #     pass

    # return redirect('shop:error')
