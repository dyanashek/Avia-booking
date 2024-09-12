import datetime
import os

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponse

from sim.models import SimCard
from sim.utils import create_excel_file

import config


@admin.register(SimCard)
class SimCardAdmin(admin.ModelAdmin):
    change_list_template = "admin/sim_change_list.html"

    search_fields = ('sim_phone',)
    fields = ('name', 'sim_phone', 'fare', 'next_payment', 'debt',)
    list_filter = ('to_main_bot', 'is_stopped', 'icount_api',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.icount_api and obj.to_main_bot:
            return [field.name for field in self.model._meta.fields]
        
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
