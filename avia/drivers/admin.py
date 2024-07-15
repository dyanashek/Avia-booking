from django.contrib import admin

from drivers.models import Driver


@admin.register(Driver)
class Driver(admin.ModelAdmin):
    list_display = ('name',)
    fields = ('name', 'telegram_id', 'circuit_id',)

