from django.contrib import admin

from errors.models import AppError


@admin.register(AppError)
class AppErrorAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'source', 'error_type', 'main_user', 'connected_user', 'resolved',)
    search_fields = ('main_user', 'connected_user',)
    list_filter = ('source', 'error_type', 'resolved',)
    date_hierarchy = 'created_at'
    readonly_fields = ('source', 'error_type', 'main_user', 'connected_user',)
