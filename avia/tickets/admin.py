import datetime
import os

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponse

from tickets.models import Ticket
from tickets.utils import create_excel_file


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    change_list_template = "admin/ticket_change_list.html"
    change_form_template = "admin/ticket_change_form.html"

    fields = ('route', 'type', 'departure_date', 'arrival_date', 'phone', 'name', 
              'family_name', 'address', 'sex', 'birth_date', 'start_date', 'end_date', 
              'passport_number', 'passport_photo_flight', 'price',
              'user',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('route', 'type', 'departure_date', 'arrival_date', 'phone', 'name', 
              'family_name', 'address', 'sex', 'birth_date', 'start_date', 'end_date', 
              'passport_number', 'passport_photo_flight', 'price',
              'user',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.circuit_api and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]
        
        return []
    
    def price_view(self, obj):
        return f'{obj.price}₪'

    def to_circuit_button(self, obj):
        if obj.circuit_api is False and obj.valid:
            return format_html(f'''
                <a class="button" href="/circuit/ticket/{obj.id}/">Circuit</a>
                ''')
        elif obj.circuit_api is True:
            return 'передано'

        return '-'
    
    def get_list_display(self, request, obj=None):
        fields = ['route', 'departure_date', 'arrival_date', 'price_view', 'to_circuit_button']

        return fields

    def price_view(self, obj):
        return f'{obj.price}₪'
    
    def save_model(self, request, obj, form, change,):
        if request.user and obj.pk is None:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)
    
    def download_report(self, request):
        date_from = datetime.datetime.strptime(request.POST.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.datetime.strptime(request.POST.get('date_to'), '%Y-%m-%d').date()
        tickets = Ticket.aggregate_report(date_from, date_to)
        if tickets.all():
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file(tickets, date_from, date_to))

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
            path('report-tickets/', self.admin_site.admin_view(self.download_report), name='report-tickets'),
        ]
        return custom_urls + urls

    price_view.short_description = 'цена'
    to_circuit_button.short_description = 'circuit'
