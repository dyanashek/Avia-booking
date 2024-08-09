from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.db import models
from django.db.models import Count, Sum, Q
from django.utils import timezone
from easy_thumbnails.files import get_thumbnailer
from filer.fields.image import FilerImageField

from core.models import TGUser, ParcelVariation, SEX_CHOICES

User = get_user_model()


class Parcel(models.Model):
    variation = models.ForeignKey(ParcelVariation, verbose_name='Вариант посылки', on_delete=models.SET_NULL, related_name='admin_parcels', null=True)
    fio_receiver = models.CharField(verbose_name='ФИО получателя', max_length=100)
    phone_receiver = models.CharField(verbose_name='Номер телефона получателя', max_length=25)
    items_list = models.TextField(verbose_name='Предметы в посылке', max_length=1024)
    name = models.CharField(verbose_name='Имя', max_length=100)
    family_name = models.CharField(verbose_name='Фамилия', max_length=100, null=True, blank=True)
    phone = models.CharField(verbose_name='Номер телефона отправителя', max_length=25)
    address = models.CharField(verbose_name='Адрес отправителя', max_length=4096)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_parcel = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_parcel_photo")
    price = models.FloatField(verbose_name='Стоимость', default=0)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='admin_parcels', null=True, blank=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(User, verbose_name='Менеджер', related_name='parcels', on_delete=models.SET_NULL, null=True, blank=True)

    valid = models.BooleanField(default=True)
    circuit_api = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'посылка'
        verbose_name_plural = 'посылки'
        ordering = ('-created_at',)
    
    def __str__(self):
        return str(self.variation)

    def get_thumbnail(self):
        image = '-'
        if self.passport_photo_parcel:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.passport_photo_parcel)['passport_thumbnail'].url)
        return image
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = u'Паспорт'

    @classmethod
    def aggregate_report(self, date_from, date_to):
        parcels = Parcel.objects.filter(
            Q(created_at__date__lte=date_to) & 
            Q(created_at__date__gte=date_from) &
            Q(created_by__isnull=False) &
            Q(circuit_api=True)
        ).values('created_by__username').annotate(
            parcels_total=Count('id'),
            parcels_sum=Sum('price'),
            )

        return parcels