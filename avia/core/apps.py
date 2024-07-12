from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Управление ботом (авиабилеты и посылки)'

    def ready(self):
        from core.tasks import run_scheduler
        run_scheduler()
