from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.db import models
from django.db.models import Count, Sum, Q
from django.utils import timezone
from easy_thumbnails.files import get_thumbnailer
from filer.fields.image import FilerImageField

from core.models import TGUser, Day, Route, FLIGHT_TYPES_CHOICES, SEX_CHOICES

User = get_user_model()

class Ticket(models.Model):
    route = models.ForeignKey(Route, verbose_name='Маршрут', on_delete=models.SET_NULL, related_name='admin_flights', null=True)
    type = models.CharField(verbose_name='Тип перелета', choices=FLIGHT_TYPES_CHOICES, max_length=15)
    departure_date = models.ForeignKey(Day, verbose_name='Дата отлета', related_name="departure_flights", on_delete=models.SET_NULL, null=True)
    arrival_date = models.ForeignKey(Day, verbose_name='Дата прилета', related_name="arrival_flights", on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(verbose_name='Номер телефона', max_length=25)
    name = models.CharField(verbose_name='Имя', max_length=100)
    family_name = models.CharField(verbose_name='Фамилия', max_length=100)
    address = models.CharField(verbose_name='Адрес', max_length=4096)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096)
    birth_date = models.DateField(verbose_name='Дата рождения')
    start_date = models.DateField(verbose_name='Дата выдачи паспорта')
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта')
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20)
    passport_photo_flight = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    price = models.FloatField(verbose_name='Стоимость в шекелях', default=0)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.SET_NULL, related_name='admin_flights', null=True, blank=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(User, verbose_name='Менеджер', related_name='tickets', on_delete=models.SET_NULL, null=True, blank=True)
    valid = models.BooleanField(default=True)
    circuit_api = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'билет'
        verbose_name_plural = 'билеты'
        ordering = ('-created_at',)
    
    def __str__(self):
        return str(f'{self.route} {self.departure_date}')

    def save(self, *args, **kwargs) -> None:
        super().save()
        if ((self.type == 'roundtrip' and not self.arrival_date) 
        or (self.type == 'oneway' and self.arrival_date)
        or ((self.arrival_date and self.arrival_date.day < timezone.now().date()) or self.departure_date.day < timezone.now().date())):
            self.valid = False
        super().save(*args, **kwargs)

    def get_thumbnail(self):
        image = '-'
        if self.passport_photo_flight:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.passport_photo_flight)['passport_thumbnail'].url)
        return image
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = u'Паспорт'

    @classmethod
    def aggregate_report(self, date_from, date_to):
        tickets = Ticket.objects.filter(
            Q(created_at__date__lte=date_to) & 
            Q(created_at__date__gte=date_from) &
            Q(created_by__isnull=False) &
            Q(circuit_api=True)
        ).values('created_by__username').annotate(
            tickets_total=Count('id'),
            tickets_sum=Sum('price'),
            )

        return tickets

