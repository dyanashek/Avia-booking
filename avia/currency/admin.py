import os
import datetime

from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from reversion.admin import VersionAdmin

from currency.models import Contractor, Operation
from currency.utils import create_excel_file

@admin.register(Contractor)
class ContractorAdmin(VersionAdmin):
    list_display = ('name', 'agent_type', 'readable_debt', 'readable_commission',)

    def readable_debt(self, obj):
        if obj.agent_type == '1':
            return f'{round(obj.debt, 2)} ₪'
        elif obj.agent_type == '2':
            if obj.debt >= 0:
                return f'{round(obj.debt, 2)} usdt'
            else:
                return f'{round(obj.debt * (1 + obj.commission / 100), 2)} $'
    
    def readable_commission(self, obj):
        return f'{obj.commission}%'

    readable_debt.short_description = 'задолженность перед контрагентом'
    readable_commission.short_description = 'комиссия'

    def has_module_permission(self, request):
        return False


@admin.register(Operation)
class OperationAdmin(VersionAdmin):
    change_list_template = "admin/operations_change_list.html"
    change_form_template = "admin/operations_change_form.html"
    date_hierarchy = 'date'
    list_filter = ('valid', 'operation_type',)
    list_display = ('contractor', 'operation_type', 'readable_amount', 'date', 'valid')
    fields = ('contractor', 'operation_type', 'amount', 'date', 'rate')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.valid:
            return [field.name for field in self.model._meta.fields]

        return []

    def readable_amount(self, obj):
        if obj.operation_type == '1':
            return f'{round(obj.amount)} usdt'
        elif obj.operation_type == '2':
            return f'{round(obj.amount)} ₪'
        elif obj.operation_type == '3':
            return f'{round(obj.amount)} $'
        elif obj.operation_type == '4':
            return f'{round(obj.amount)} usdt'

    readable_amount.short_description = 'сумма операции'

    def download_report(self, request):
        date_from = datetime.datetime.strptime(request.POST.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(request.POST.get('date_to'), '%Y-%m-%d').date()
        operations = Operation.aggregate_report(date_from, date_to)
        if operations:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file(operations, date_from, date_to))

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
            path('currency-operations/', self.admin_site.admin_view(self.download_report), name='currency_operations'),
        ]
        return custom_urls + urls
    
    def has_module_permission(self, request):
        return False
        