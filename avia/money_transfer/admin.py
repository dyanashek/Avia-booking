from django.contrib import admin
from money_transfer.models import Manager, Sender, Receiver, Address, Transfer, Delivery, Rate, Commission, Status
from adminsortable2.admin import SortableAdminMixin
from reversion.admin import VersionAdmin


class TransferInline(admin.StackedInline):
    model = Transfer
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.valid:
            return [field.name for field in self.model._meta.fields]

        return []


@admin.register(Manager)
class ManagerAdmin(VersionAdmin):
    list_display = ('telegram_id', 'updated_at')
    date_hierarchy = 'updated_at'


@admin.register(Address)
class AddressAdmin(VersionAdmin):
    list_display = ('address',)
    search_fields = ('address',)
    date_hierarchy = 'updated_at'

    def has_module_permission(self, request):
        return False


@admin.register(Sender)
class SenderAdmin(VersionAdmin):
    list_display = ('name', 'phone',)
    search_fields = ('name', 'phone',)
    fields = ('name', 'phone',)

    def has_module_permission(self, request):
        return False


@admin.register(Receiver)
class ReceiverAdmin(VersionAdmin):
    list_display = ('name', 'phone',)
    search_fields = ('name', 'phone')
    fields = ('name', 'phone',)

    def has_module_permission(self, request):
        return False


@admin.register(Delivery)
class DeliveryAdmin(VersionAdmin):
    fields = ('sender', 'sender_address', 'usd_amount', 'ils_amount', 'commission')
    list_display = ('pk', 'sender', 'final_commission', 'valid', 'status_message')
    search_fields = ('sender__name', 'sender__phone',)
    list_filter = ('valid', 'status')
    inlines = (TransferInline,)
    autocomplete_fields = ('sender',)

    def final_commission(self, obj):
        if obj.commission == 0:
            return '-'
        return f'{obj.commission}₪'

    final_commission.short_description = 'комиссия'

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.valid:
            return [field.name for field in self.model._meta.fields]

        return ('commission', 'valid', 'status_message', 'circuit_id')


@admin.register(Rate)
class RateAdmin(VersionAdmin):
    list_display = ('slug', 'rate',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.slug:
            return ('slug',)

        return []


@admin.register(Commission)
class CommissionAdmin(SortableAdminMixin, VersionAdmin):
    list_display = ('commission', 'diapason', 'order')

    def commission(self, obj):
        symbol = '₪'
        if obj.unit == 1:
            symbol = '%'

        return f'{obj.value}{symbol}'
    
    def diapason(self, obj):
        high_value = f'{obj.high_value}$'
        if not obj.high_value:
            high_value = '~'
        return f'От {obj.low_value}$ до {high_value}'

    commission.short_description = 'комиссия'
    diapason.short_description = 'диапазон'


@admin.register(Status)
class StatusAdmin(VersionAdmin):
    list_display = ('slug', 'text',)

    def has_module_permission(self, request):
        return False