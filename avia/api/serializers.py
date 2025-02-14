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
)


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

    class Meta:
        model = Cart
        fields = ["id", "total_sum", "items"]


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "item_count", "total_sum", "readable_total_sum"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    readable_time = serializers.SerializerMethodField()
    readable_date = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "total_sum", "items", "readable_total_sum", "status", "created_at", "readable_time", "readable_date"]

    def get_readable_time(self, obj):
        return obj.readable_time

    def get_readable_date(self, obj):
        return obj.readable_date


class FavoriteProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    in_cart = serializers.BooleanField(default=False)
    item_count = serializers.IntegerField(default=0)

    class Meta:
        model = FavoriteProduct
        fields = ["id", "product", "in_cart", 'item_count']
