from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin

from core.models import Language, TGText, ParcelVariation, Day, Route, TGUser, Parcel, Flight


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

    def add_language(self, request, queryset):
        selected_language = queryset.first().language
        added_language = Language.objects.last()

        if not TGText.objects.filter(language=added_language).exists():
            for text in TGText.objects.filter(language=selected_language).all()[::-1]:
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

        if not ParcelVariation.objects.filter(language=added_language).exists():
            for variation in ParcelVariation.objects.filter(language=selected_language).all()[::-1]:
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
    list_display = ('username', 'name', 'family_name', 'get_thumbnail')
    readonly_fields = ('passport_photo_id',)


@admin.register(Parcel)
class ParcelAdmin(admin.ModelAdmin):
    list_display = ('family_name', 'variation', 'get_thumbnail', 'complete', 'confirmed')
    list_filter = ('complete', 'confirmed')
    readonly_fields = ('passport_photo_id', 'confirmed', 'circuit_id')


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('family_name', 'route', 'departure_date', 'arrival_date', 'get_thumbnail', 'complete', 'confirmed')
    list_filter = ('complete', 'confirmed', 'departure_date', 'arrival_date')
    readonly_fields = ('passport_photo_id', 'confirmed', 'circuit_id')