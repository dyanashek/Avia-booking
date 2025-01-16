from django.contrib import admin

from drivers.models import Driver


@admin.register(Driver)
class Driver(admin.ModelAdmin):
    list_display = ('name',)
    fields = ('name', 'telegram_id', 'circuit_id',)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return [field.name for field in self.model._meta.fields if not field.name in ('created_at', 'id')]
        else:
            return ('name', 'telegram_id', 'circuit_id',)
