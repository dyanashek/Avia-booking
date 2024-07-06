from django.apps import AppConfig


class MoneyTransferConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'money_transfer'
    verbose_name = 'Денежные переводы'