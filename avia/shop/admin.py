from django.contrib import admin
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
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
   BuyerProfile,
   BaseSettings,
   OrderStatus,
)


@admin.register(Category)
class CategoryAdmin(SortableAdminMixin, VersionAdmin):
    list_display = ('__str__', 'get_link', 'order',)
    search_fields = ('title',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)
    
    def get_link(self, obj):
        base_settings = BaseSettings.objects.first()
        if base_settings.bot_name and obj.id:
            return format_html(
                '<div class="readonly">'
                '<input type="text" value="{}" readonly style="width: 400px;" '
                'onclick="this.select(); document.execCommand(\'copy\');">'
                '</div>',
                f'https://t.me/{base_settings.bot_name}?start=cat{obj.id}'
            )
        return "-"
    get_link.short_description = 'Ссылка'


@admin.register(SubCategory)
class SubCategoryAdmin(SortableAdminMixin, VersionAdmin):
    list_display = ('__str__', 'category', 'get_link', 'order',)
    search_fields = ('title', 'category__title')
    list_filter = ('category',)
    autocomplete_fields = ('category',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)
    
    def get_link(self, obj):
        base_settings = BaseSettings.objects.first()
        if base_settings.bot_name and obj.id:
            return format_html(
                '<div class="readonly">'
                '<input type="text" value="{}" readonly style="width: 400px;" '
                'onclick="this.select(); document.execCommand(\'copy\');">'
                '</div>',
                f'https://t.me/{base_settings.bot_name}?start=subcat{obj.id}'
            )
        return "-"
    get_link.short_description = 'Ссылка'


@admin.register(ProductUnit)
class ProductUnitAdmin(VersionAdmin):
    list_display = ('__str__',)
    search_fields = ('title',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)
    

@admin.register(Product)
class ProductAdmin(SortableAdminMixin, VersionAdmin):
    change_form_template = 'admin/product_change_from.html'
    list_display = ('title', 'get_thumbnail', 'price', 'category', 'subcategory', 'unit', 'in_stoplist', 'get_link', 'order',)
    search_fields = ('title', 'category__title', 'subcategory__title',)
    list_filter = ('category', 'subcategory', 'in_stoplist')
    autocomplete_fields = ('category', 'unit',)

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)

    def get_link(self, obj):
        base_settings = BaseSettings.objects.first()
        if base_settings.bot_name and obj.id:
            return format_html(
                '<div class="readonly">'
                '<input type="text" value="{}" readonly style="width: 400px;" '
                'onclick="this.select(); document.execCommand(\'copy\');">'
                '</div>',
                f'https://t.me/{base_settings.bot_name}?start=product{obj.id}'
            )
        return "-"
    get_link.short_description = 'Ссылка'


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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if obj.status == OrderStatus.Completed or obj.status == OrderStatus.Canceled:
            return ['product', 'item_count',]
        return []

    def has_add_permission(self, request, obj=None):
        if obj.status == OrderStatus.Completed or obj.status == OrderStatus.Canceled:
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj.status == OrderStatus.Completed or obj.status == OrderStatus.Canceled:
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        if obj.status == OrderStatus.Completed or obj.status == OrderStatus.Canceled:
            return False
        return True


@admin.register(Order)
class OrderAdmin(VersionAdmin):
    list_display = ('user', 'status', 'created_at', 'date', 'time', 'paid',)
    search_fields = ('user__username', 'address', 'phone',)
    list_filter = ('status', 'paid',)
    inlines = [OrderItemInline]

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)

    def get_readonly_fields(self, request, obj=None):
        if obj.status == OrderStatus.Completed or obj.status == OrderStatus.Canceled:
            return ['user', 'address', 'phone', 'created_at', 'date', 'time', 'status', 'paid',]
        return []

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
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
    

@admin.register(BuyerProfile)
class BuyerProfileAdmin(VersionAdmin):
    list_display = ('user', 'tg_id', 'phone', 'address',)
    search_fields = ('user__username', 'tg_id', 'phone',)
    autocomplete_fields = ('user',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return super().has_module_permission(request)


@admin.register(BaseSettings)
class BaseSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings, _ = BaseSettings.objects.get_or_create(pk=1)
        if settings:
            return HttpResponseRedirect(
                reverse('admin:shop_basesettings_change', args=[settings.id])
            )
        else:
            settings = BaseSettings.objects.create()
            return HttpResponseRedirect(
                reverse('admin:shop_basesettings_change', args=[settings.id])
            )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = "Редактирование настроек"
        return super().change_view(request, object_id, form_url, extra_context)
    
    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)
