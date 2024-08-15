from django.apps import AppConfig


class MoneyTransferConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'money_transfer'
    verbose_name = 'Денежные переводы'

    def ready(self):
        try:
            from money_transfer.models import Balance
            
            Balance.objects.get_or_create(id=1)
        except:
            pass