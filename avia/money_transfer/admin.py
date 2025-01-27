import os
import datetime

from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.utils.html import format_html
from reversion.admin import VersionAdmin

from money_transfer.utils import create_excel_file, create_excel_file_drivers, create_excel_file_debit_credit
from money_transfer.models import (Manager, Sender, Receiver, Address, Transfer, 
                                   Delivery, Rate, Commission, Status, DebitCredit,
                                   Balance, BuyRate, Report)
from adminsortable2.admin import SortableAdminMixin
from money_transfer.formsets import TransferInlineFormSet


class TransferInline(admin.StackedInline):
    model = Transfer
    #formset = TransferInlineFormSet
    extra = 0
    fields = ('delivery', 'receiver', 'address', 'pick_up', 'usd_amount',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.valid and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]

        elif request.user.is_superuser:
            return tuple()

        return ('pass_date',)


@admin.register(Manager)
class ManagerAdmin(VersionAdmin):
    list_display = ('name', 'telegram_id', 'updated_at',)
    date_hierarchy = 'updated_at'
    fields = ('name', 'telegram_id',)

        
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
    change_list_template = "admin/delivery_change_list.html"
    change_form_template = "admin/delivery_change_form.html"
    search_fields = ('sender__name', 'sender__phone',)
    list_filter = ('valid', 'status', 'created_by', 'driver', 'created_by_callcenter', 'approved_by_client',)
    inlines = (TransferInline,)
    autocomplete_fields = ('sender',)
    
    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('sender', 'sender_address', 'usd_amount', 'ils_amount', 'total_usd', 'commission', 'driver', 'invite_client')

    def final_commission(self, obj):
        if obj.commission == 0:
            return '-'
        return f'{obj.commission}₪'

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.valid and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]
        elif request.user.is_superuser:
            return tuple()
        return ('commission', 'valid', 'status_message', 'circuit_id', 'total_usd', 'driver', 'invite_client',)

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
            user_groups = request.user.groups.all()
            for group in user_groups:
                if group.name == 'Call-center':
                    obj.created_by_callcenter = True
                    obj.approved_by_client = None
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

    def to_circuit_button(self, obj):
        if obj.circuit_api is False:
            return format_html(f'''
                <a class="button" href="/circuit/delivery/{obj.id}/">Circuit</a>
                ''')

        return '-'

    def to_gspread_button(self, obj):
        if obj.gspread_api is False:
            return format_html(f'''
                <a class="button" href="/gspread/delivery/{obj.id}/">GoogleSheets</a>
                ''')

        return '-'
    
    def get_list_display(self, request, obj=None):
        fields = ['pk', 'sender', 'final_commission', 'valid', 'status_message', 'receivers_codes', 'created_at', 'invite_client']
        for delivery in super().get_queryset(request):
            if delivery.circuit_api is False:
                if 'to_circuit_button' not in fields:
                    fields.append('to_circuit_button')
            if delivery.gspread_api is False:
                if 'to_gspread_button' not in fields:
                    fields.append('to_gspread_button')

        return fields

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        rate = Rate.objects.filter(slug='usd-ils').first()
        if rate:
            extra_context['rate'] = str(rate.rate)
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        rate = Rate.objects.filter(slug='usd-ils').first()
        if rate:
            extra_context['rate'] = str(rate.rate)
        return super().add_view(request, form_url, extra_context=extra_context)

    final_commission.short_description = 'комиссия'
    receivers_codes.short_description = 'коды для получения'
    to_circuit_button.short_description = 'circuit'
    to_gspread_button.short_description = 'google таблица'


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


class DatePassedFilter(admin.SimpleListFilter):
    title = 'передано получателю'
    parameter_name = 'date_received'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(pass_date__isnull=False)
        if self.value() == 'no':
            return queryset.filter(pass_date__isnull=True)
        return queryset

        
@admin.register(Transfer)
class TransferAdmin(VersionAdmin):
    list_display = ('pk', 'usd_amount', 'pass_date', 'credit',)
    date_hierarchy = 'pass_date'
    search_fields = ('pk',)
    list_filter = (DatePassedFilter, 'credit',)
    readonly_fields = ('delivery', 'receiver', 'address', 'pick_up', 'usd_amount')

    def has_module_permission(self, request):
        if request.user.groups.count() == 1 and request.user.groups.first().name == 'Call-center':
            return False
        return True


@admin.register(DebitCredit)
class DebitCreditAdmin(VersionAdmin):
    change_list_template = "admin/debit_credit_change_list.html"
    list_display = ('date', 'amount', 'operation_type')
    list_filter = ('operation_type',)

    def download_report(self, request):
        date_from = datetime.datetime.strptime(request.POST.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(request.POST.get('date_to'), '%Y-%m-%d').date()
        debit_credit = DebitCredit.aggregate_report(date_from, date_to)
        if debit_credit:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file_debit_credit(debit_credit, date_from, date_to))

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
            path('debit-credit/', self.admin_site.admin_view(self.download_report), name='debit_credit'),
        ]
        return custom_urls + urls


@admin.register(Balance)
class BalanceAdmin(VersionAdmin):
    list_display = ('debt_firms', 'debt_ravshan', 'balance')

    def has_module_permission(self, request):
        return False


@admin.register(BuyRate)
class BuyRateAdmin(VersionAdmin):
    list_display = ('date', 'rate',)

    def has_module_permission(self, request):
        return False


@admin.register(Report)
class ReportAdmin(VersionAdmin):
    change_list_template = "admin/report_change_list.html"
    list_display = ('report_date', 'first_driver', 'second_driver', 'third_driver', 'total_stats',)
    date_hierarchy = 'report_date'

    def first_driver(self, obj):
        return f'{obj.first_driver_usd}$ | {obj.first_driver_ils}₪ | +{obj.first_driver_commission}₪ ({obj.first_driver_points})'
    
    def second_driver(self, obj):
        return f'{obj.second_driver_usd}$ | {obj.second_driver_ils}₪ | +{obj.second_driver_commission}₪ ({obj.second_driver_points})'

    def third_driver(self, obj):
        return f'{obj.third_driver_usd}$ | {obj.third_driver_ils}₪ | +{obj.third_driver_commission}₪ ({obj.third_driver_points})'

    def total_stats(self, obj):
        return f'{obj.total_usd}$ | {obj.total_ils}₪ | +{obj.total_commission}₪ ({obj.total_points})'

    first_driver.short_description = 'первый водитель'
    second_driver.short_description = 'второй водитель'
    third_driver.short_description = 'третий водитель'
    total_stats.short_description = 'итого'

    def download_report(self, request):
        date_from = datetime.datetime.strptime(request.POST.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(request.POST.get('date_to'), '%Y-%m-%d').date()
        report = Report.aggregate_report(date_from, date_to)
        if report:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file_drivers(report, date_from, date_to))

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
            path('report-drivers/', self.admin_site.admin_view(self.download_report), name='report_drivers'),
        ]
        return custom_urls + urls
