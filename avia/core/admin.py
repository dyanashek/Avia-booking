import os

from django.contrib import admin
from django.db.models import Q
from django.urls import path
from django.utils.html import format_html
from django.http import HttpResponse
from adminsortable2.admin import SortableAdminMixin

from core.models import (Language, TGText, ParcelVariation, Day, Route, TGUser, Parcel, Flight, SimFare, 
                         UsersSim, Notification, OldSim, ImprovedNotification, LinkButton, Receipt,
                         UserMessage, Question)
from core.utils import create_excel_file


@admin.register(Language)
class LanguageAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('language', 'slug', 'my_order',)
    search_fields = ('language',)


@admin.register(TGText)
class TGTextAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('slug', 'text', 'language', 'my_order',)
    list_filter = ('language',)
    search_fields = ('text', 'slug',)
    actions = ('add_language',)
    readonly_fields = ('slug',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.slug and not request.user.is_superuser:
            return ('slug',)

        return tuple()

    def add_language(self, request, queryset):
        selected_language = queryset.first().language
        added_language = Language.objects.last()

        for text in TGText.objects.filter(language=selected_language).all()[::-1]:
            if not TGText.objects.filter(Q(slug=text.slug) & Q(language=added_language)).exists():
                TGText(slug=text.slug, text=text.text, language=added_language).save()
            elif text.slug == 'month':
                if TGText.objects.filter(Q(slug=text.slug) & Q(language=added_language)).count() < 12:
                    TGText(slug=text.slug, text=text.text, language=added_language).save()
        
    add_language.short_description = "Добавить другой язык"


@admin.register(ParcelVariation)
class ParcelVariationAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'language', 'my_order',)
    list_filter = ('language',)
    actions = ('add_language',)

    def add_language(self, request, queryset):
        selected_language = queryset.first().language
        added_language = Language.objects.last()

        for variation in ParcelVariation.objects.filter(language=selected_language).all()[::-1]:
            if not ParcelVariation.objects.filter(Q(name=variation.name) & Q(language=added_language)).exists():
                ParcelVariation(name=variation.name, language=added_language).save()
        
    add_language.short_description = "Добавить другой язык"


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ('day',)


@admin.register(Route)
class RouteAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('route', 'my_order',)
    filter_horizontal = ('days',)


@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    change_form_template = "admin/dialog_button.html"
    list_display = ('user_id', 'username', 'active', 'name', 'family_name', 'get_thumbnail')
    search_fields = ('user_id', 'username', 'name', 'family_name', 'sim_cards__sim_phone',)
    readonly_fields = ('created_at', 'active',)
    list_filter = ('active', 'language',)
    fields = ('user_id', 'language', 'username', 'active', 'name', 'family_name',
              'phone', 'addresses', 'lat', 'lon', 'sex', 'birth_date', 'start_date',
               'end_date', 'passport_number', 'passport_photo_user', 'created_at')

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('user_id', 'language', 'username', 'active', 'name', 'family_name',
              'phone', 'addresses', 'lat', 'lon', 'sex', 'birth_date', 'start_date',
               'end_date', 'passport_number', 'passport_photo_user', 'created_at')

    def has_module_permission(self, request):
        if request.user.groups.count() == 1 and request.user.groups.first().name == 'Call-center':
            return False
        return True


@admin.register(Parcel)
class ParcelAdmin(admin.ModelAdmin):
    list_filter = ('complete', 'confirmed')
    fields = ('variation', 'fio_receiver', 'phone_receiver', 'items_list',
              'name', 'family_name', 'phone', 'address', 'sex', 'birth_date',
              'start_date', 'end_date', 'passport_number', 'passport_photo_parcel',
              'complete', 'confirmed', 'price', 'user', 'created_at')
    
    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('variation', 'fio_receiver', 'phone_receiver', 'items_list',
              'name', 'family_name', 'phone', 'address', 'sex', 'birth_date',
              'start_date', 'end_date', 'passport_number', 'passport_photo_parcel',
              'complete', 'confirmed', 'price', 'user', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.id and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]
        return tuple()
    
    def to_circuit_button(self, obj):
        if obj.circuit_api is False:
            return format_html(f'''
                <a class="button" href="/circuit/parcel/{obj.id}/">Circuit</a>
                ''')

        return '-'
    
    def get_list_display(self, request, obj=None):
        fields = ['family_name', 'variation', 'get_thumbnail', 'complete', 'confirmed']

        for parcel in super().get_queryset(request):
            if parcel.circuit_api is False:
                if 'to_circuit_button' not in fields:
                    fields.append('to_circuit_button')

        return fields

    to_circuit_button.short_description = 'circuit'


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_filter = ('complete', 'confirmed', 'departure_date', 'arrival_date')
    fields = ('route', 'type', 'departure_date', 'arrival_date', 'phone', 'name', 
              'family_name', 'address', 'sex', 'birth_date', 'start_date', 'end_date', 
              'passport_number', 'passport_photo_flight', 'complete', 'confirmed', 'price',
              'user', 'created_at',)
    
    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('route', 'type', 'departure_date', 'arrival_date', 'phone', 'name', 
              'family_name', 'address', 'sex', 'birth_date', 'start_date', 'end_date', 
              'passport_number', 'passport_photo_flight', 'complete', 'confirmed', 'price',
              'user', 'created_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.id and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]
        return tuple()

    def to_circuit_button(self, obj):
        if obj.circuit_api is False:
            return format_html(f'''
                <a class="button" href="/circuit/flight/{obj.id}/">Circuit</a>
                ''')

        return '-'
    
    def get_list_display(self, request, obj=None):
        fields = ['family_name', 'route', 'departure_date', 'arrival_date', 
                  'get_thumbnail', 'complete', 'confirmed']

        for flight in super().get_queryset(request):
            if flight.circuit_api is False:
                if 'to_circuit_button' not in fields:
                    fields.append('to_circuit_button')

        return fields

    to_circuit_button.short_description = 'circuit'


@admin.register(SimFare)
class SimFareAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('title', 'price', 'my_order')


@admin.register(UsersSim)
class UsersSimAdmin(admin.ModelAdmin):
    change_form_template = "admin/dialog_button_sim.html"
    change_list_template = "admin/sims_change_list.html"
    list_filter = ('ready_to_pay', 'is_old_sim', 'is_stopped',)
    search_fields = ('sim_phone',)
    fields = ('user', 'fare', 'debt', 'sim_phone', 'next_payment', 'pay_date', 'ready_to_pay', 'is_old_sim', 'driver',)
    readonly_fields = ('driver', 'is_old_sim',)
    autocomplete_fields = ('user',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('user', 'fare', 'debt', 'sim_phone', 'next_payment', 'pay_date', 'ready_to_pay', 'is_old_sim', 'driver',)

    def to_circuit_button(self, obj):
        if obj.circuit_api is False and obj.icount_api:
            return format_html(f'''
                <a class="button" href="/circuit/sim/{obj.id}/">Circuit</a>
                ''')

        return '-'
    
    def to_icount_button(self, obj):
        if obj.icount_api is False:
            return format_html(f'''
                <a class="button" href="/icount/sim/{obj.id}/">iCount</a>
                ''')

        return '-'

    def to_circuit_collect_button(self, obj):
        if obj.circuit_api_collect is False:
            return format_html(f'''
                <a class="button" href="/circuit/sim-collect/{obj.id}/">Circuit</a>
                ''')

        return '-'
    
    def to_icount_collect_button(self, obj):
        if obj.icount_api_collect is False and obj.icount_collect_amount > 0:
            return format_html(f'''
                <a class="button" href="/icount/sim-collect/{obj.id}/">iCount</a>
                ''')

        return '-'

    def get_list_display(self, request, obj=None):
        fields = ['user', 'fare', 'debt', 'ready_to_pay', 'is_stopped']

        for sim in super().get_queryset(request):
            if sim.circuit_api is False and sim.icount_api:
                if 'to_circuit_button' not in fields:
                    fields.append('to_circuit_button')
            
            if sim.icount_api is False:
                if 'to_icount_button' not in fields:
                    fields.append('to_icount_button')

            if sim.circuit_api_collect is False:
                if 'to_circuit_collect_button' not in fields:
                    fields.append('to_circuit_collect_button')
            
            if sim.icount_api_collect is False and sim.icount_collect_amount > 0:
                if 'to_icount_collect_button' not in fields:
                    fields.append('to_icount_collect_button')
            
        return fields
    
    to_circuit_button.short_description = 'circuit (доставка)'
    to_icount_button.short_description = 'iCount (клиент)'
    to_circuit_collect_button.short_description = 'circuit (сбор)'
    to_icount_collect_button.short_description = 'iCount (чек)'

    def download_report(self, request):
        sims = UsersSim.aggregate_report()
        if sims.all():
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file(sims, old=False))

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
            path('report/', self.admin_site.admin_view(self.download_report), name='report_sims'),
        ]
        return custom_urls + urls


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notify_time', 'notified')
    list_filter = ('notified',)
    fields = ('user', 'text', 'notify_now', 'notify_time', 'notified')
    autocomplete_fields = ('user',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('user', 'text', 'notify_now', 'notify_time', 'notified')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.notified and not request.user.is_superuser:
            return ('user', 'text', 'notify_now', 'notify_time', 'notified')

        return ('notified',)
    
    def has_module_permission(self, request):
        return False


@admin.register(OldSim)
class OldSimAdmin(admin.ModelAdmin):
    change_list_template = "admin/old_sims_change_list.html"
    list_display = ('sim_phone', 'debt', 'to_main_bot')
    search_fields = ('sim_phone',)
    readonly_fields = ('user_id', 'sim_phone', 'fare', 'to_main_bot', 'icount_id')
    list_filter = ('to_main_bot',)

    def download_report(self, request):
        old_sims = OldSim.aggregate_report()
        if old_sims.all():
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, create_excel_file(old_sims))

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
            path('report/', self.admin_site.admin_view(self.download_report), name='report_old_sims'),
        ]
        return custom_urls + urls
    
    def has_module_permission(self, request):
        return False


class LinkButtonInline(admin.StackedInline):
    model = LinkButton
    extra = 0
    fields = ('text', 'link',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.started and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]
        else:
            return []


@admin.register(ImprovedNotification)
class ImprovedNotificationAdmin(admin.ModelAdmin):
    list_display = ('notify_time', 'target', 'is_valid', 'started', 'notified', 'curr_status',)
    list_filter = ('is_valid', 'started', 'notified', 'target',)
    fields = ('target', 'user', 'text', 'notify_time', 'image',)
    inlines = (LinkButtonInline,)
    autocomplete_fields = ('user',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('target', 'user', 'text', 'notify_time', 'image',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.started and not request.user.is_superuser:
            return [field.name for field in self.model._meta.fields]
        else:
            return []
    
    def curr_status(self, obj):
        if obj and obj.total_users > 0:
            return f'{obj.success_users}/{obj.total_send_users}/{obj.total_users}'
        
        return '-/-/-'
    
    curr_status.short_description = 'Успешно/Отправлено/Всего'


@admin.register(Receipt)
class ReceiptNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'link', 'notify_time', 'success',)
    list_filter = ('success',)
    search_fields = ('user__user_id', 'user__sim_cards__sim_phone',)


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    change_list_template = "admin/user_messages_list.html"

    list_display = ('user', 'created_at',)
    readonly_fields = ('user', 'message',)
    date_hierarchy = 'created_at'


@admin.register(Question)
class QuestionAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ('question_rus', 'order',)
    search_fields = ('question_rus',)
