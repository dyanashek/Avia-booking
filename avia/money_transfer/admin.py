import os
import datetime

from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from reversion.admin import VersionAdmin

from money_transfer.utils import create_excel_file
from money_transfer.models import Manager, Sender, Receiver, Address, Transfer, Delivery, Rate, Commission, Status
from adminsortable2.admin import SortableAdminMixin


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

    def has_module_permission(self, request):
        return False
        
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
    search_fields = ('name', 'phone', 'user__user_id', 'user__username')
    fields = ('name', 'phone', 'user')
    autocomplete_fields = ('user',)

    def has_module_permission(self, request):
        return False


@admin.register(Receiver)
class ReceiverAdmin(VersionAdmin):
    list_display = ('name', 'phone',)
    search_fields = ('name', 'phone', 'user__user_id', 'user__username')
    fields = ('name', 'phone', 'user')
    autocomplete_fields = ('user',)

    def has_module_permission(self, request):
        return False


@admin.register(Delivery)
class DeliveryAdmin(VersionAdmin):
    # change_list_template = "admin/delivery_change_list.html"
    fields = ('sender', 'sender_address', 'usd_amount', 'ils_amount', 'total_usd', 'commission')
    list_display = ('pk', 'sender', 'final_commission', 'valid', 'status_message', 'receivers_codes')
    search_fields = ('sender__name', 'sender__phone',)
    list_filter = ('valid', 'status', 'created_by')
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

        return ('commission', 'valid', 'status_message', 'circuit_id', 'total_usd',)

    def download_report(self, request):
        date_from = datetime.datetime.strptime(request.POST.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(request.POST.get('date_to'), '%Y-%m-%d').date()
        deliveries = Delivery.aggregate_report(date_from, date_to)
        if deliveries.all():
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file(deliveries, date_from, date_to))

            if os.path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", status=200)
                    response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return response
            else:
                return HttpResponse("Файл не найден", status=404)
        else:
            return HttpResponse("Данные за указанный период отсутствуют", status=400)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('report/', self.admin_site.admin_view(self.download_report), name='report'),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change,):
        if request.user and obj.pk is None:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

    def receivers_codes(self, obj):
        if obj.transfers.all():
            codes = ''
            for transfer in obj.transfers.all():
                codes += f', {transfer.pk}'
            codes = codes.lstrip(', ')
        else:
            codes = '-'
        return codes

    receivers_codes.short_description = 'коды для получения'

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