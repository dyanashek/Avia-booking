from typing import Any
from django.contrib import admin
from django.conf import settings
from django.http import HttpRequest, HttpResponseRedirect
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
   TopupRequest,
   TopupRequestStatus,
   BalanceTransaction,
   AccessToken,
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
    fields = ('product', 'item_count', 'product_price', 'total_sum',)
    verbose_name_plural = 'Товары'

    def product_price(self, obj):
        return obj.product.price
    product_price.short_description = 'Цена продукта'

    def get_readonly_fields(self, request, obj=None):
        return ['total_sum', 'product_price', 'product', 'item_count']

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

    def total_sum(self, obj):
        return obj.product.price * obj.item_count
    total_sum.short_description = 'Сумма'


@admin.register(Order)
class OrderAdmin(VersionAdmin):
    search_fields = ('user__username', 'address', 'phone',)
    list_filter = ('status',)
    exclude = ('paid',)

    inlines = [OrderItemInline]

    def has_module_permission(self, request):
        if settings.HIDE_SHOP:
            return False
        return super().has_module_permission(request)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ['user', 'address', 'phone', 'created_at', 'delivery_price', 'date', 'time', 'status', 'circuit_id', 'icount_url', 'driver', 'driver_comment', 'total_sum',]
        return ['user', 'address', 'phone', 'created_at', 'delivery_price', 'date', 'time', 'status', 'icount_url', 'driver', 'driver_comment', 'total_sum',]

    def get_readonly_fields(self, request, obj=None):
        if obj.status != OrderStatus.Created and not request.user.is_superuser:
            return ['user', 'address', 'phone', 'created_at', 'delivery_price', 'date', 'time', 'status', 'circuit_id', 'icount_url', 'driver', 'driver_comment', 'total_sum',]
        return ['created_at', 'total_sum',]

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def to_circuit_button(self, obj):
        if not obj.circuit_id and obj.status == OrderStatus.AwaitingDelivery:
            return format_html(f'''
                <a class="button" href="/circuit/order/{obj.id}/"> Circuit</a>
                ''')

        return '-'
    to_circuit_button.short_description = 'Отправить в Circuit'

    def to_icount_button(self, obj):
        if not obj.icount_url and obj.status == OrderStatus.Completed:
            return format_html(f'''
                <a class="button" href="/icount/order/{obj.id}/">iCount</a>
                ''')

        return '-'
    to_icount_button.short_description = 'Отправить в iCount'

    def get_list_display(self, request, obj=None):
        fields = ['user', 'status', 'created_at', 'date', 'time', 'driver',]

        for order in super().get_queryset(request):
            if not order.circuit_id and order.status == OrderStatus.AwaitingDelivery and 'to_circuit_button' not in fields:
                fields.append('to_circuit_button')
            if not order.icount_url and order.status == OrderStatus.Completed and 'to_icount_button' not in fields:
                fields.append('to_icount_button')
            if 'to_icount_button' in fields and 'to_circuit_button' in fields:
                break
            
        return fields
    
    def total_sum(self, obj):
        return obj.total_sum
    total_sum.short_description = 'Сумма'


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
    search_fields = ('user__username', 'tg_id', 'phone',)
    autocomplete_fields = ('user',)

    def has_module_permission(self, request):
        if request.user.is_superuser and not settings.HIDE_SHOP:
            return True
        return super().has_module_permission(request)
    
    def get_exclude(self, request, obj=None):
        if not request.user.is_superuser:
            return ['icount_id',]
        return []

    def to_icount_button(self, obj):
        if not obj.icount_id and obj.israel_phone:
            return format_html(f'''
                <a class="button" href="/icount/buyer/{obj.id}/">iCount</a>
                ''')

        return '-'
    to_icount_button.short_description = 'Отправить в iCount'

    def get_list_display(self, request, obj=None):
        fields = ['user', 'tg_id', 'phone', 'address', 'israel_phone', 'israel_address',]

        for buyer in super().get_queryset(request):
            if not buyer.icount_id and buyer.israel_phone and 'to_icount_button' not in fields:
                fields.append('to_icount_button')
                break
            
        return fields


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


@admin.register(TopupRequest)
class TopupRequestAdmin(VersionAdmin):
    search_fields = ('user__username',)
    list_filter = ('status',)

    def get_exclude(self, request: HttpRequest, obj: Any | None = ...) -> Any:
        if request.user.is_superuser:
            return []
        return ('circuit_id',)
    
    def to_circuit_button(self, obj):
        if not obj.circuit_id and obj.status == TopupRequestStatus.Awaiting:
            return format_html(f'''
                <a class="button" href="/circuit/topup/{obj.id}/"> Circuit</a>
                ''')

        return '-'
    to_circuit_button.short_description = 'Отправить в Circuit'

    def get_list_display(self, request, obj=None):
        fields = ['user', 'status', 'created_at', 'amount', 'driver',]

        for topup in super().get_queryset(request):
            if not topup.circuit_id and topup.status == TopupRequestStatus.Awaiting and 'to_circuit_button' not in fields:
                fields.append('to_circuit_button')
                break
            
        return fields
    
    def get_readonly_fields(self, request, obj=None):
        if obj.status == TopupRequestStatus.Completed or obj.status == TopupRequestStatus.Canceled:
            return ['user', 'created_at', 'amount', 'phone', 'address', 'status', 'circuit_id', 'driver', 'driver_comment',]
        return ['created_at',]
    

@admin.register(BalanceTransaction)
class BalanceTransactionAdmin(VersionAdmin):
    list_display = ('sender', 'receiver', 'amount', 'created_at',)
    search_fields = ('sender__username', 'receiver__username',)
    list_filter = ('created_at',)
    

@admin.register(AccessToken)
class AccessTokenAdmin(VersionAdmin):
    list_display = ('token', 'is_used',)
    search_fields = ('token',)
    list_filter = ('is_used',)
    
    def has_module_permission(self, request):
        return False
    