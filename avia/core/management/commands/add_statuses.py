from django.core.management import BaseCommand
from django.db.models import Q

from money_transfer.models import Status

class Command(BaseCommand):
    def handle(self, *args, **options):
        statuses = [
            ['save_error', 'Ошибка при валидации данных'],
            ['saved',	'Доставка сохранена'],
            ['api',	'Данные по доставке переданы в Circuit'],
            ['api_error', 'Ошибка передачи данных в Circuit'],
            ['finished', 'Получено от отправителя'],
            ['attempted', 'Не удалось забрать у отправителя'],
            ['waiting', 'Ожидает подтверждения клиентом'],
            ['cancelled', 'Отменено клиентом'],
        ]
        
        for item in statuses:
            slug = item[0]
            text = item[1]
            if not Status.objects.filter(slug=slug).exists():
                Status.objects.create(
                    slug=slug,
                    text=text,
                )
        
        print('done')

