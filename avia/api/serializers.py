import math

from rest_framework import serializers

from shop.models import (
    Product,
    Category,
    SubCategory,
    ProductUnit,
    FavoriteProduct,
    Cart,
    CartItem,
    Order,
    OrderItem,
    BaseSettings,
    BuyerProfile,
)
from shop.utils import format_amount


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "title",]


class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = SubCategory
        fields = ["id", "title", "category"]


class ProductUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUnit
        fields = ["id", "title"]


class ProductSerializer(serializers.ModelSerializer):
    in_fav = serializers.BooleanField(default=False)
    in_cart = serializers.BooleanField(default=False)
    cover = serializers.SerializerMethodField()
    category = CategorySerializer()
    subcategory = SubCategorySerializer()
    unit = ProductUnitSerializer()
    item_count = serializers.IntegerField(default=0)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "price",
            "readable_price",
            "cover",
            "description",
            "in_fav",
            "in_cart",
            "category",
            "subcategory",
            "unit",
            "item_count",
        ]

    def get_cover(self, obj):
        if obj.cover:
            return obj.cover.url
        return None


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = CartItem
        fields = ["id", "product", "item_count", "total_sum", "readable_total_sum"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)
    delivery_price = serializers.SerializerMethodField()
    free_delivery = serializers.SerializerMethodField()
    delivery_price_readable = serializers.SerializerMethodField()
    free_delivery_readable = serializers.SerializerMethodField()
    buyer_balance = serializers.SerializerMethodField()
    topup_amount = serializers.SerializerMethodField()
    order_possible = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "total_sum", "items", "cart_total_sum", "delivery_price", 
                  "free_delivery", "delivery_price_readable", "free_delivery_readable", 
                  "buyer_balance", "topup_amount", "order_possible"]

    def get_order_possible(self, obj):
        if buyer:= BuyerProfile.objects.filter(user=obj.user).first():
            return obj.cart_total_sum <= buyer.balance
        return False

    def get_delivery_price(self, obj):
        return BaseSettings.objects.first().delivery_price

    def get_free_delivery(self, obj):
        return BaseSettings.objects.first().free_delivery

    def get_delivery_price_readable(self, obj):
        return format_amount(BaseSettings.objects.first().delivery_price)

    def get_free_delivery_readable(self, obj):
        return format_amount(BaseSettings.objects.first().free_delivery)

    def get_buyer_balance(self, obj):
        if buyer:= BuyerProfile.objects.filter(user=obj.user).first():
            return buyer.balance
        return 0

    def get_topup_amount(self, obj):
        balance = 0
        if buyer:= BuyerProfile.objects.filter(user=obj.user).first():
            balance = buyer.balance
        return math.ceil(obj.cart_total_sum - balance)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "item_count", "total_sum", "readable_total_sum"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    readable_time = serializers.SerializerMethodField()
    readable_date = serializers.SerializerMethodField()
    readable_delivery_date = serializers.SerializerMethodField()
    readable_delivery_time = serializers.SerializerMethodField()
    delivery_price_readable = serializers.SerializerMethodField()


    class Meta:
        model = Order
        fields = ["id", "total_sum", "items", "readable_total_sum", "status", "created_at", "readable_time", "readable_date",
                  "address", "phone", "readable_delivery_date", "readable_delivery_time", 'delivery_price', 'delivery_price_readable']

    def get_readable_time(self, obj):
        return obj.readable_time

    def get_readable_date(self, obj):
        return obj.readable_date

    def get_readable_delivery_date(self, obj):
        return obj.readable_delivery_date

    def get_readable_delivery_time(self, obj):
        return obj.readable_delivery_time

    def get_delivery_price_readable(self, obj):
        return format_amount(obj.delivery_price)


class FavoriteProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    in_cart = serializers.BooleanField(default=False)
    item_count = serializers.IntegerField(default=0)

    class Meta:
        model = FavoriteProduct
        fields = ["id", "product", "in_cart", 'item_count']
