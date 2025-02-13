from django.contrib import admin
from django.conf import settings
from adminsortable2.admin import SortableAdminMixin
from reversion.admin import VersionAdmin

from .models import (
   Product,
   ProductUnit,
   Category,
   SubCategory,
   FavoriteProduct,
   Cart,
   CartItem,
   Order,
   OrderItem,
)


@admin.register(Category)
class CategoryAdmin(SortableAdminMixin, VersionAdmin):
    list_display = ('__str__', 'order',)
    search_fields = ('title',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return True
    

@admin.register(SubCategory)
class SubCategoryAdmin(SortableAdminMixin, VersionAdmin):
    list_display = ('__str__', 'category', 'order',)
    search_fields = ('title', 'category__title')
    list_filter = ('category',)
    autocomplete_fields = ('category',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return True
    

@admin.register(ProductUnit)
class ProductUnitAdmin(VersionAdmin):
    list_display = ('__str__',)
    search_fields = ('title',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return True
    

@admin.register(Product)
class ProductAdmin(SortableAdminMixin, VersionAdmin):
    change_form_template = 'admin/product_change_from.html'
    list_display = ('title', 'get_thumbnail', 'price', 'category', 'subcategory', 'unit', 'in_stoplist', 'order',)
    search_fields = ('title', 'category__title', 'subcategory__title',)
    list_filter = ('category', 'subcategory', 'in_stoplist')
    autocomplete_fields = ('category', 'unit',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return True


@admin.register(FavoriteProduct)
class FavoriteProductAdmin(VersionAdmin):
    list_display = ('user', 'product',)
    search_fields = ('user__username', 'product__title',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return False
    

@admin.register(Cart)
class CartAdmin(VersionAdmin):
    list_display = ('user', 'total_sum',)
    search_fields = ('user__username',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return False
    

@admin.register(CartItem)
class CartItemAdmin(VersionAdmin):
    list_display = ('cart', 'product', 'item_count',)
    search_fields = ('cart__user__username', 'product__title',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return False


@admin.register(Order)
class OrderAdmin(VersionAdmin):
    list_display = ('user', 'status', 'created_at',)
    search_fields = ('user__username',)
    list_filter = ('status',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return False


@admin.register(OrderItem)
class OrderItemAdmin(VersionAdmin):
    list_display = ('product', 'item_count',)
    search_fields = ('order__user__username', 'product__title',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return False
    