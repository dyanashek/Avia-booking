import datetime

from django.db import models
from django.utils.html import format_html
from django.db.models.signals import post_save
from django.dispatch import receiver
from easy_thumbnails.files import get_thumbnailer
from filer.fields.image import FilerImageField
from django_ckeditor_5.fields import CKEditor5Field

from core.utils import send_message_on_telegram
from drivers.models import Driver
from config import MESSAGES_CHAT_ID, DOMAIN

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
    lat = models.FloatField(verbose_name='Широта', null=True, blank=True, default=None)
    lon = models.FloatField(verbose_name='Долгота', null=True, blank=True, default=None)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_user = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    passport_photo_id = models.CharField(verbose_name='TG id паспорта', max_length=200, null=True, blank=True)
    curr_input = models.CharField(verbose_name='Текущий ввод', max_length=100, null=True, blank=True, default=None)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    active = models.BooleanField(verbose_name='Пользователь активен?', default=True)

    class Meta:
        verbose_name = 'клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ('-created_at',)
    
    def __str__(self):
        if self.username:
            result = f'@{self.username} {self.user_id}'
        elif self.name:
            result = f'{self.name} {self.user_id}'
        else:
            result = self.user_id
        
        if self.sim_cards.first():
            result += f' ({self.sim_cards.first().sim_phone})'
        
        return result
    
    def get_thumbnail(self):
        image = '-'
        if self.passport_photo_user:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.passport_photo_user)['passport_thumbnail'].url)
        return image
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = u'Паспорт'

    @property
    def newest_message(self):
        outbox = datetime.datetime.min
        inbox = datetime.datetime.min
        if self.stupid_messages.first():
            outbox = self.stupid_messages.first().created_at
        if self.notifications.first():
            inbox = self.notifications.first().notify_time
        
        return max(outbox, inbox)


class Parcel(models.Model):
    variation = models.ForeignKey(ParcelVariation, verbose_name='Вариант посылки', on_delete=models.SET_NULL, related_name='parcels', null=True)
    fio_receiver = models.CharField(verbose_name='ФИО получателя', max_length=100, null=True, blank=True)
    phone_receiver = models.CharField(verbose_name='Номер телефона получателя', max_length=25, null=True, blank=True)
    items_list = models.TextField(verbose_name='Предметы в посылке', max_length=1024, null=True, blank=True)
    name = models.CharField(verbose_name='Имя', max_length=100, null=True, blank=True)
    family_name = models.CharField(verbose_name='Фамилия', max_length=100, null=True, blank=True)
    phone = models.CharField(verbose_name='Номер телефона отправителя', max_length=25, null=True, blank=True)
    address = models.CharField(verbose_name='Адрес отправителя', max_length=4096, null=True, blank=True)
    lat = models.FloatField(verbose_name='Широта', null=True, blank=True, default=None)
    lon = models.FloatField(verbose_name='Долгота', null=True, blank=True, default=None)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_parcel = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    passport_photo_id = models.CharField(verbose_name='TG id паспорта', max_length=200, null=True, blank=True)
    complete = models.BooleanField(verbose_name='Заявка подтверждена пользователем', null=True, blank=True, default=None)
    confirmed = models.BooleanField(verbose_name='Заявка подтверждена менеджером', null=True, blank=True, default=None)
    price = models.FloatField(verbose_name='Стоимость', default=0)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='parcels', null=True, blank=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)

    circuit_api = models.BooleanField(null=True, blank=True, default=None)

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
    lat = models.FloatField(verbose_name='Широта', null=True, blank=True, default=None)
    lon = models.FloatField(verbose_name='Долгота', null=True, blank=True, default=None)
    sex = models.CharField(verbose_name='Пол', choices=SEX_CHOICES, max_length=4096, null=True, blank=True)
    birth_date = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    start_date = models.DateField(verbose_name='Дата выдачи паспорта', null=True, blank=True)
    end_date = models.DateField(verbose_name='Дата окончания срока действия паспорта', null=True, blank=True)
    passport_number = models.CharField(verbose_name='Номер паспорта', max_length=20, null=True, blank=True)
    passport_photo_flight = FilerImageField(verbose_name='Фото паспорта', on_delete=models.SET_NULL, null=True, blank=True)
    passport_photo_id = models.CharField(verbose_name='TG id паспорта', max_length=200, null=True, blank=True)
    complete = models.BooleanField(verbose_name='Заявка подтверждена пользователем', null=True, blank=True, default=None)
    confirmed = models.BooleanField(verbose_name='Заявка подтверждена менеджером', null=True, blank=True, default=None)
    price = models.FloatField(verbose_name='Стоимость', default=0)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='flights', null=True, blank=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)

    circuit_api = models.BooleanField(null=True, blank=True, default=None)

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
    debt = models.FloatField(verbose_name='Задолженность', help_text='Отрицательная, при оплате наперед.')
    ready_to_pay = models.BooleanField(verbose_name='Готов оплачивать', default=False)
    notified = models.BooleanField(verbose_name='Уведомлен сегодня', default=False)
    circuit_id = models.CharField(verbose_name='Circuit id (delivery_sim)', max_length=250, blank=True, null=True, unique=True)
    icount_id = models.IntegerField(null=True, blank=True, default=None)
    circuit_id_collect = models.CharField(verbose_name='Circuit id (collect money)', help_text='После получения денег - удалить.', max_length=250, blank=True, null=True, unique=True)
    driver = models.ForeignKey(Driver, verbose_name='Водитель', help_text='Последний водитель, вносивший информацию через бота о переданных клиентом деньгах', on_delete=models.SET_NULL, related_name='sim_cards', null=True, blank=True)
    is_old_sim = models.BooleanField(verbose_name='Старая симка?', default=False)
    is_stopped = models.BooleanField(verbose_name='Приостановлен', default=False)
    
    circuit_api = models.BooleanField(null=True, blank=True, default=None)
    icount_api = models.BooleanField(null=True, blank=True, default=None)
    circuit_api_collect = models.BooleanField(null=True, blank=True, default=None)
    icount_api_collect = models.BooleanField(null=True, blank=True, default=None)
    icount_collect_amount = models.FloatField(default=0.0)
    # алгоритм поиска тех, кому направлять уведомления: 
    # !-> смотрим у кого next_payment=today() и начисляем по тарифу dept
    # !-> dept больше определенного значения, ready_to_pay=False, pay_date=None
    # !-> после нахождения таких ставим им pay_date=today() и notified=False 
    # !-> сразу после ищем тех, у кого pay_date=today и ready_to_pay=False и notified=False
    # !-> отправляем им сообщения с вариантами "готов платить", "через неделю", "через месяц"
    # !-> если готов платить - меняем ready_to_pay на True, notified на False, pay_date на today() и добавляем в circuit
    # !-> если нет, то переносим pay_date на нужное количество дней, notified меняем на False
    # !-> когда водитель забрал деньги - меняем pay_date на None, ready_to_pay на False, удаляем circuit_id
    # ?-> отправляем менеджеру (водителю) вопрос, сколько денег забрал водитель
    # ?-> вычитаем сумму из dept
    
    class Meta:
        verbose_name = 'сим карта'
        verbose_name_plural = 'сим карты'
        ordering = ('-created_at',)
    
    def __str__(self):
        return self.sim_phone

    @classmethod
    def aggregate_report(self):
        return UsersSim.objects.values('sim_phone', 'debt')

    @property
    def not_received(self):
        if self.circuit_id and self.collects.count() == 0:
            return True
        return False


class Notification(models.Model):
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    text = models.TextField(verbose_name='Текст уведомления')
    notify_now = models.BooleanField(verbose_name='Уведомить сейчас', default=True)
    notify_time = models.DateTimeField(verbose_name='Время уведомления', help_text='Указывается в UTC (-3 от МСК). Игнорируется, если активно поле "уведомить сейчас".', null=True, blank=True)
    notified = models.BooleanField(verbose_name='Уведомлен', null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'уведомление пользователя'
        verbose_name_plural = 'уведомления пользователей'
        ordering = ('-notify_time',)
    
    def __str__(self):
        return str(self.user)


class OldSim(models.Model):
    user_id = models.CharField(verbose_name='Телеграм id', max_length=100, unique=True, null=True, blank=True, default=None)
    sim_phone = models.CharField(verbose_name='Номер симкарты', max_length=100, unique=True)
    fare = models.ForeignKey(SimFare, verbose_name='Тариф', on_delete=models.CASCADE, related_name='old_sims', null=True, blank=True)
    address = models.CharField(verbose_name='Адрес', max_length=512, null=True, blank=True, default=None)
    name = models.CharField(verbose_name='Имя', max_length=512, null=True, blank=True, default=None)
    debt = models.FloatField(verbose_name='Задолженность')
    next_payment = models.DateField(verbose_name='Дата следующего платежа')
    to_main_bot = models.BooleanField(verbose_name='Перенесена в основного бота?', default=False)
    icount_id = models.IntegerField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'старая сим карта'
        verbose_name_plural = 'старые сим карты'
    
    def __str__(self):
        return self.sim_phone

    @classmethod
    def aggregate_report(self):
        return OldSim.objects.values('sim_phone', 'debt')


NOTIFICATION_TYPES = (
    ('1', 'Индивидуальное'),
    ('2', 'Всем пользователям')
)


class LinkButton(models.Model):
    notification = models.ForeignKey('ImprovedNotification', verbose_name='Уведомление', on_delete=models.CASCADE, related_name='buttons')
    text = models.CharField(verbose_name='Текст (русский)', max_length=50)
    link = models.CharField(verbose_name='Ссылка', max_length=1024, help_text='Обязательно должна содержать "https://"')
    my_order = models.PositiveIntegerField(verbose_name='Порядок', default=0, blank=False, null=False)

    class Meta:
        verbose_name = 'кнопка с ссылкой'
        verbose_name_plural = 'кнопки с ссылками'
        ordering = ('my_order',)
    
    def __str__(self):
        return self.link


class ImprovedNotification(models.Model):
    target = models.CharField(verbose_name='Тип уведомления', choices=NOTIFICATION_TYPES, max_length=30)
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='improved_notifications', null=True, blank=True, help_text='Учитывается только если выбран тип "индивидуальное"')
    text = CKEditor5Field(verbose_name='Текст уведомления (русский)')
    notify_time = models.DateTimeField(verbose_name='Время уведомления', help_text='Указывается в UTC (-3 от МСК).')
    image = FilerImageField(verbose_name='Изображение', on_delete=models.SET_NULL, null=True, blank=True)
    is_valid = models.BooleanField(verbose_name='Рассылка валидна?', default=False) 
    started = models.BooleanField(verbose_name='Рассылка началась?', default=False) 
    notified = models.BooleanField(verbose_name='Успешно?', null=True, blank=True, default=None)

    success_users = models.IntegerField(default=0)
    total_send_users = models.IntegerField(default=0)
    total_users = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'уведомление пользователей'
        verbose_name_plural = 'уведомления пользователей'
        ordering = ('-notify_time',)
    
    def __str__(self):
        return self.target
    
    def save(self, *args, **kwargs) -> None:
        if self.text == '<p>&nbsp;</p>':
            self.is_valid = False

        elif self.target == '1' and self.user is None:
            self.is_valid = False
        
        else:
            self.is_valid = True
        
        if self.pk:
            if self.buttons.all():
                for button in self.buttons.all():
                    if 'https://' not in button.link:
                        self.is_valid = False
                        break

        super().save(*args, **kwargs)


class Receipt(models.Model):
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', related_name='receipts', on_delete=models.CASCADE)
    link = models.URLField(verbose_name='Ссылка')
    notify_time = models.DateTimeField(verbose_name='Время отправки', help_text='Указывается в UTC (-3 от МСК).')
    success = models.BooleanField(verbose_name='Успешно?', null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'квитанция'
        verbose_name_plural = 'квитанции'
        ordering = ('-notify_time',)


class UserMessage(models.Model):
    user = models.ForeignKey(TGUser, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='stupid_messages', null=True, blank=True)
    message = models.TextField(verbose_name='Текст', null=True, blank=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'сообщение от пользователя'
        verbose_name_plural = 'сообщения от пользователей'
        ordering = ('-created_at',)
    
    def save(self, *args, **kwargs) -> None:
        text = f'*TG id:* {self.user.user_id}'
        if self.user.username:
            text += f'\n*Имя пользователя: @{self.user.username}*'
        
        try:
            phone = self.user.sim_cards.first().sim_phone
        except:
            phone = None
        
        if phone:
            text += f'\n*Номер сим карты*: {phone}'

        text += f'\n\n*Сообщение:*\n{self.message}'
        text += f'\n\n[Диалог с пользователем]({DOMAIN}/dialog/{self.user.user_id})'
        params = {
                'chat_id': MESSAGES_CHAT_ID,
                'text': text,
                'parse_mode': "Markdown",
            }
        send_message_on_telegram(params)
        super().save(*args, **kwargs)


class Question(models.Model):
    question_rus = models.CharField(verbose_name='Текст вопроса (русский)', max_length=256)
    question_uzb = models.CharField(verbose_name='Текст вопроса (узбекский)', max_length=256)
    answer_rus = CKEditor5Field(verbose_name='Текст ответа (русский)')
    answer_uzb = CKEditor5Field(verbose_name='Текст ответа (узбекский)')
    order = models.PositiveIntegerField(verbose_name='Порядок', default=0, blank=False, null=False)

    class Meta:
        verbose_name = 'вопрос-ответ'
        verbose_name_plural = 'FAQ'
        ordering = ('order',)

    def __str__(self):
        return self.question_rus


@receiver(post_save, sender=Notification)
def handle_notification(sender, instance, **kwargs):
    if instance.notify_now and instance.notified is None:
        params = {
                'chat_id': instance.user.user_id,
                'text': instance.text,
            }

        try:
            response = send_message_on_telegram(params)
            instance.notified = True
        except:
            response = None
            instance.notified = False
        
        instance.notify_time = datetime.datetime.utcnow()
        instance.save()

        if 'https:' in instance.text:
            success = False
            try:
                if response.json().get('ok'):
                    success = True
            except:
                pass
            
            link = 'https:' + instance.text.split('https:')[-1]
            Receipt.objects.create(
                user=instance.user,
                link=link,
                notify_time=instance.notify_time,
                success=success,
            )
