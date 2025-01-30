import datetime
import os

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponse
from reversion.admin import VersionAdmin

from sim.models import SimCard, Collect, Report
from sim.utils import create_excel_file, create_excel_file_drivers

import config


@admin.register(SimCard)
class SimCardAdmin(admin.ModelAdmin):
    change_list_template = "admin/sim_change_list.html"

    search_fields = ('sim_phone',)
    fields = ('name', 'sim_phone', 'fare', 'next_payment', 'debt', 'is_stopped',)
    list_filter = ('to_main_bot', 'is_stopped', 'icount_api',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('name', 'sim_phone', 'fare', 'next_payment', 'debt', 'is_stopped',)
              
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.icount_api and obj.to_main_bot and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('is_stopped',)]
        
        return []

    def to_icount_button(self, obj):
        if obj.name is None:
            return 'необходимо указать имя'

        if obj.icount_api is False:
            return format_html(f'''
                <a class="button" href="/icount/admin-sim/{obj.id}/">iCount</a>
                ''')
        elif obj.icount_api is True:
            return 'передано'

        return '-'
    
    def ref_link(self, obj):
        if obj and obj.sim_phone:
            return f'https://t.me/{config.TELEGRAM_BOT}?start={obj.sim_phone}'
        return '-'
    
    def get_list_display(self, request, obj=None):
        fields = ['name', 'fare', 'debt', 'to_main_bot', 'to_icount_button', 'ref_link', 'is_stopped']

        return fields
    
    def save_model(self, request, obj, form, change,):
        if request.user and obj.pk is None:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)
    
    def download_report(self, request):
        date_from = datetime.datetime.strptime(request.POST.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(request.POST.get('date_to'), '%Y-%m-%d').date()
        sim_cards = SimCard.aggregate_report(date_from, date_to)
        if sim_cards.all():
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file(sim_cards, date_from, date_to))

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
            path('report-sims/', self.admin_site.admin_view(self.download_report), name='report-sims'),
        ]
        return custom_urls + urls

    to_icount_button.short_description = 'icount'
    ref_link.short_description = 'ссылка'


@admin.register(Collect)
class CollectAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = ('sim', 'driver', 'created_at', 'amount',)
    list_filter = ('driver',)
    autocomplete_fields = ('sim',)
    search_fields = ('sim__sim_phone',)


@admin.register(Report)
class ReportAdmin(VersionAdmin):
    change_list_template = "admin/sim_report_change_list.html"
    list_display = ('report_date', 'first_driver', 'second_driver', 'third_driver', 'total_stats',)
    date_hierarchy = 'report_date'
    search_fields = ('sim__sim_phone',)

    def first_driver(self, obj):
        return f'{obj.first_driver_ils}₪ ({obj.first_driver_points})'
    
    def second_driver(self, obj):
        return f'{obj.second_driver_ils}₪ ({obj.second_driver_points})'

    def third_driver(self, obj):
        return f'{obj.third_driver_ils}₪ ({obj.third_driver_points})'

    def total_stats(self, obj):
        return f'{obj.total_ils}₪ ({obj.total_points})'

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
            path('sim-report-drivers/', self.admin_site.admin_view(self.download_report), name='sim_report_drivers'),
        ]
        return custom_urls + urls
