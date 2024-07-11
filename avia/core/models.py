from django.db import models
from django.utils.html import format_html
from django.db.models.signals import post_save
from django.dispatch import receiver
from easy_thumbnails.files import get_thumbnailer
from filer.fields.image import FilerImageField

from core.utils import send_pickup_address

SEX_CHOICES = (
    ('M', 'Мужской',),
    ('F', 'Женский',),
)


FLIGHT_TYPES_CHOICES = (
    ('oneway', 'В одну сторону'),
    ('roundtrip', 'Туда-обратно'),
)


class Language(models.Model):
    language = models.CharField(verbose_name='Язык', max_length=100, unique=True)
    slug = models.CharField(verbose_name='Идентификатор', max_length=100, unique=True)
    my_order = models.PositiveIntegerField(verbose_name='Порядок', default=0, blank=False, null=False)

    class Meta:
        verbose_name = 'язык'
        verbose_name_plural = 'языки'
        ordering = ('my_order',)

    def __str__(self):
        return self.language


class TGText(models.Model):
    slug = models.CharField(verbose_name='Идентификатор', max_length=100)
    text = models.TextField(verbose_name='Текст', max_length=4096)
    language = models.ForeignKey(Language, verbose_name='Язык', on_delete=models.CASCADE, related_name='texts', blank=True, null=True)
    my_order = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta:
        verbose_name = 'текст'
        verbose_name_plural = 'Текстовое наполнение'
        ordering = ('my_order',)
    
    def __str__(self):
        return self.text


class ParcelVariation(models.Model):
    name = models.CharField(verbose_name='Вариант посылки', max_length=100)
    my_order = models.PositiveIntegerField(default=0, blank=False, null=False)
    language = models.ForeignKey(Language, verbose_name='Язык', on_delete=models.CASCADE, related_name='parcel_variations')

    class Meta:
        verbose_name = 'вариант посылки'
        verbose_name_plural = 'Варианты посылки'
        ordering = ('my_order',)
    
    def __str__(self):
        return self.name


class Day(models.Model):
    day = models.DateField(verbose_name='Число')

    class Meta:
        verbose_name = 'число'
        verbose_name_plural = 'числа'
        ordering = ('day',)
    
    def __str__(self):
        return self.day.strftime('%d.%m.%Y')


class Route(models.Model):
    route = models.CharField(verbose_name='Маршрут', max_length=100, unique=True)
    days = models.ManyToManyField(Day, verbose_name='Числа', blank=True)
    opposite = models.ForeignKey('self', on_delete=models.CASCADE, related_name='flight_opposite', blank=True, null=True)
    my_order = models.PositiveIntegerField(verbose_name='Порядок', default=0, blank=False, null=False)

    class Meta:
        verbose_name = 'маршрут'
        verbose_name_plural = 'маршруты'
        ordering = ('my_order',)

    def __str__(self):
        return self.route


class TGUser(models.Model):
    user_id = models.CharField(verbose_name='Телеграм id', max_length=100, unique=True)
    language = models.ForeignKey(Language, verbose_name='Язык', on_delete=models.SET_NULL, related_name='users', null=True,)
    username = models.CharField(verbose_name='Ник телеграм', max_length=100, null=True, blank=True)
    name = models.CharField(verbose_name='Имя', max_length=100, null=True, blank=True)
    family_name = models.CharField(verbose_name='Фамилия', max_length=100, null=True, blank=True)
    phone = models.CharField(verbose_name='Номер телефона', max_length=25, null=True, blank=True)
    addresses = models.CharField(verbose_name='Адреса', max_length=4096, null=True, blank=True)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_user = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    passport_photo_id = models.CharField(verbose_name='TG id паспорта', max_length=200, null=True, blank=True)
    curr_input = models.CharField(verbose_name='Текущий ввод', max_length=100, null=True, blank=True, default=None)
    
    class Meta:
        verbose_name = 'клиент'
        verbose_name_plural = 'Клиенты'
    
    def __str__(self):
        if self.name:
            return self.name
        elif self.username:
            return self.username
        else:
            return self.user_id
    
    def get_thumbnail(self):
        image = '-'
        if self.passport_photo_user:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.passport_photo_user)['passport_thumbnail'].url)
        return image
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = u'Паспорт'


class Parcel(models.Model):
    variation = models.ForeignKey(ParcelVariation, verbose_name='Вариант посылки', on_delete=models.SET_NULL, related_name='parcels', null=True)
    fio_receiver = models.CharField(verbose_name='ФИО получателя', max_length=100, null=True, blank=True)
    phone_receiver = models.CharField(verbose_name='Номер телефона получателя', max_length=25, null=True, blank=True)
    items_list = models.TextField(verbose_name='Предметы в посылке', max_length=1024, null=True, blank=True)
    name = models.CharField(verbose_name='Имя', max_length=100, null=True, blank=True)
    family_name = models.CharField(verbose_name='Фамилия', max_length=100, null=True, blank=True)
    phone = models.CharField(verbose_name='Номер телефона отправителя', max_length=25, null=True, blank=True)
    address = models.CharField(verbose_name='Адрес отправителя', max_length=4096, null=True, blank=True)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_parcel = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    passport_photo_id = models.CharField(verbose_name='TG id паспорта', max_length=200, null=True, blank=True)
    complete = models.BooleanField(verbose_name='Заявка подтверждена пользователем', null=True, blank=True, default=None)
    # finished = models.BooleanField(verbose_name='Заявка обработана', null=True, blank=True, default=False)
    confirmed = models.BooleanField(verbose_name='Заявка подтверждена менеджером', null=True, blank=True, default=None)
    price = models.FloatField(verbose_name='Стоимость', default=0)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='parcels', null=True, blank=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)

    class Meta:
        verbose_name = 'посылка'
        verbose_name_plural = 'посылки'
    
    def __str__(self):
        return str(self.variation)

    def get_thumbnail(self):
        image = '-'
        if self.passport_photo_parcel:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.passport_photo_parcel)['passport_thumbnail'].url)
        return image
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = u'Паспорт'


class Flight(models.Model):
    route = models.ForeignKey(Route, verbose_name='Маршрут', on_delete=models.SET_NULL, related_name='flights', null=True)
    type = models.CharField(verbose_name='Тип перелета', choices=FLIGHT_TYPES_CHOICES, max_length=15, null=True, blank=True)
    departure_date = models.DateField(verbose_name='Дата отлета', null=True, blank=True)
    arrival_date = models.DateField(verbose_name='Дата прилета', null=True, blank=True)
    phone = models.CharField(verbose_name='Номер телефона', max_length=25, null=True, blank=True)
    name = models.CharField(verbose_name='Имя', max_length=100, null=True, blank=True)
    family_name = models.CharField(verbose_name='Фамилия', max_length=100, null=True, blank=True)
    address = models.CharField(verbose_name='Адрес', max_length=4096, null=True, blank=True)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_flight = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    passport_photo_id = models.CharField(verbose_name='TG id паспорта', max_length=200, null=True, blank=True)
    complete = models.BooleanField(verbose_name='Заявка подтверждена пользователем', null=True, blank=True, default=None)
    # finished = models.BooleanField(verbose_name='Заявка обработана', null=True, blank=True, default=False)
    confirmed = models.BooleanField(verbose_name='Заявка подтверждена менеджером', null=True, blank=True, default=None)
    price = models.FloatField(verbose_name='Стоимость', default=0)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='flights', null=True, blank=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)

    class Meta:
        verbose_name = 'перелет'
        verbose_name_plural = 'перелеты'
    
    def __str__(self):
        return str(self.user.user_id)

    def get_thumbnail(self):
        image = '-'
        if self.passport_photo_flight:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.passport_photo_flight)['passport_thumbnail'].url)
        return image
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = u'Паспорт'


class SimFare(models.Model):
    title = models.CharField(verbose_name='Название тарифа', help_text='Отобразится на кнопке', max_length=100)
    description = models.TextField(verbose_name='Описание тарифа')
    price = models.FloatField(verbose_name='Ежемесячная стоимость')
    my_order = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta:
        verbose_name = 'тариф симки'
        verbose_name_plural = 'тарифы симок'
        ordering = ('my_order',)
    
    def __str__(self):
        return self.title


class UsersSim(models.Model):
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='sim_cards', null=True, blank=True)
    fare = models.ForeignKey(SimFare, verbose_name='Тариф', on_delete=models.CASCADE, related_name='sims', null=True, blank=True)
    sim_phone = models.CharField(verbose_name='Номер телефона', max_length=25, unique=True)
    created_at = models.DateField(verbose_name='Дата приобретения', auto_now_add=True)
    next_payment = models.DateField(verbose_name='Дата следующего платежа')
    pay_date = models.DateField(verbose_name='Планируемая дата оплаты', null=True, blank=True)
    debt = models.FloatField(verbose_name='Задолженность', help_text='Отрицательная, при оплате наперед')
    ready_to_pay = models.BooleanField(verbose_name='Готов оплачивать', default=False)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)

    # алгоритм поиска тех, кому направлять уведомления: 
    # -> смотрим у кого next_payment=today() и начисляем по тарифу dept
    # -> dept больше определенного значения, ready_to_pay=False, pay_date=None
    # -> после нахождения таких ставим им pay_date=today() 
    # -> сразу после ищем тех, у кого pay_date=today и ready_to_pay=False
    # -> отправляем им сообщения с вариантами "готов платить", "через неделю", "через месяц"
    # -> если готов платить - меняем ready_to_pay на True и добавляем в circuit
    # -> если нет, то переносим pay_date на нужное количество дней
    # -> когда водитель забрал деньги - меняем pay_date на None, ready_to_pay на False
    # и отправляем менеджеру вопрос, сколько денег забрал водитель
    # -> вычитаем сумму из dept
    
    class Meta:
        verbose_name = 'сим карта'
        verbose_name_plural = 'сим карты'
        ordering = ('-created_at',)
    
    def __str__(self):
        return self.sim_phone