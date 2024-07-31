from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count, Sum, Q, Case, When, F, Value
from django.db.models.functions import Coalesce

from money_transfer.utils import send_pickup_address, delivery_to_gspread


User = get_user_model()


class Manager(models.Model):
    name = models.CharField(verbose_name='Имя', max_length=100, null=True, blank=True, default=None)
    telegram_id = models.CharField(verbose_name='Telegram id', max_length=100, unique=True)
    updated_at = models.DateTimeField(verbose_name='Последнее обновление', auto_now=True)

    class Meta:
        verbose_name = 'менеджер'
        verbose_name_plural = 'менеджеры'
        ordering = ('-updated_at',)

    def __str__(self):
        return self.telegram_id


class Address(models.Model):
    address = models.CharField(verbose_name='Адрес', max_length=250)
    updated_at = models.DateTimeField(verbose_name='Последнее обновление', auto_now=True)

    class Meta:
        verbose_name = 'адрес'
        verbose_name_plural = 'адреса'
        ordering = ('-updated_at',)

    def __str__(self):
        return self.address


class Sender(models.Model):
    user = models.OneToOneField('core.TGUser', verbose_name='Пользователь tg', on_delete=models.SET_NULL, related_name='sender', null=True, blank=True)
    name = models.CharField(verbose_name='Имя', max_length=100)
    phone = models.CharField(verbose_name='Номер телефона', max_length=100, unique=True)
    addresses = models.ManyToManyField(Address, verbose_name='Адреса', related_name='senders_addresses', blank=True)
    receivers = models.ManyToManyField('Receiver', verbose_name='Получатели', related_name='senders', blank=True)
    updated_at = models.DateTimeField(verbose_name='Последнее обновление', auto_now=True)

    class Meta:
        verbose_name = 'отправитель'
        verbose_name_plural = 'отправители'
        ordering = ('-updated_at',)

    def __str__(self):
        result =  f'{self.name} - {self.phone}'
        if self.user:
            if self.user.username:
                result += f' - @{self.user.username}'
            result += f' - tg_id: {self.user.user_id}'
        
        return result


class Receiver(models.Model):
    user = models.OneToOneField('core.TGUser', verbose_name='Пользователь tg', on_delete=models.SET_NULL, related_name='receiver', null=True, blank=True)
    name = models.CharField(verbose_name='Имя', max_length=100)
    phone = models.CharField(verbose_name='Номер телефона', max_length=100)
    addresses = models.ManyToManyField(Address, verbose_name='Адреса', related_name='receivers_addresses', blank=True)
    updated_at = models.DateTimeField(verbose_name='Последнее обновление', auto_now=True)

    class Meta:
        verbose_name = 'получатель'
        verbose_name_plural = 'получатели'
        ordering = ('-updated_at',)

    def __str__(self):
        result =  f'{self.name} - {self.phone}'
        if self.user:
            if self.user.username:
                result += f' - @{self.user.username}'
            result += f' - tg_id: {self.user.user_id}'
        
        return result


class Transfer(models.Model):
    delivery = models.ForeignKey('Delivery', related_name='transfers', on_delete=models.CASCADE)
    receiver = models.ForeignKey(Receiver, verbose_name='Получатель', related_name='transfers', on_delete=models.CASCADE)
    address = models.ForeignKey(Address, verbose_name='Адрес получателя', related_name='receivers_deliveries', blank=True, null=True, on_delete=models.SET_NULL)
    pick_up = models.BooleanField(verbose_name='Доставка до адреса', default=False)
    usd_amount = models.FloatField(verbose_name='Сумма в долларах', default=0)
    pass_date = models.DateTimeField(verbose_name='Передано получателю', null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'перевод'
        verbose_name_plural = 'переводы'

    def __str__(self):
        return f'({self.pk}) {self.receiver.name} - {self.receiver.phone}'

    def save(self, *args, **kwargs) -> None:
        super().save()
        if self.address and self.address.address != 'Samarkand':
            self.receiver.addresses.add(self.address)
            self.receiver.save()
        else:
            if self.pick_up:
                address = Address(address='Samarkand')
                address.save()
                self.address = address
        
        self.delivery.sender.receivers.add(self.receiver)
        self.delivery.sender.save()

        super().save(*args, **kwargs)


class Delivery(models.Model):
    sender = models.ForeignKey(Sender, verbose_name='Отправитель', related_name='deliveries', on_delete=models.CASCADE)
    sender_address = models.ForeignKey(Address, verbose_name='Адрес отправителя', related_name='senders_deliveries', null=True, on_delete=models.SET_NULL)
    usd_amount = models.FloatField(verbose_name='Сумма в долларах', default=0)
    ils_amount = models.FloatField(verbose_name='Сумма в шекелях', default=0)
    total_usd = models.FloatField(verbose_name='Итого в долларах', help_text='Рассчитается автоматически', default=0)
    valid = models.BooleanField(verbose_name='Валидный заказ', blank=True, null=True, default=None)
    status_message = models.CharField(verbose_name='Статус заказа', blank=True, null=True, max_length=200)
    status = models.ForeignKey('Status', verbose_name='Статус', null=True, default=None, on_delete=models.SET_NULL)
    commission = models.FloatField(verbose_name='Комиссия (₪)', help_text='Рассчитается автоматически', default=0)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=250, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    created_by = models.ForeignKey(User, verbose_name='Менеджер', related_name='deliveries', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'доставки'

    def __str__(self):
        return f'{self.sender.name} - {self.sender.phone}'

    def save(self, *args, **kwargs) -> None:
        self.sender.addresses.add(self.sender_address)
        self.sender.save()

        super().save(*args, **kwargs)
    
    def calculate_total_usd_amount(self):
        ils_rate = Rate.objects.get(slug='usd-ils').rate
        usd_amount = self.usd_amount + self.ils_amount / ils_rate
        return usd_amount

    def calculate_commission(self):
        usd_amount = self.calculate_total_usd_amount()
        commission = Commission.objects.filter(Q(Q(low_value__lte=usd_amount) & Q(high_value__gte=usd_amount)) | 
                                Q(Q(low_value__lte=usd_amount) & Q(high_value__isnull=True))).first()
        
        if commission:
            unit = commission.unit
            value = commission.value

            if unit == 1:
                rate = Rate.objects.get(slug='usd-ils').rate
                commission = usd_amount * rate * (value / 100)
            else:
                commission = value
        
        return commission

    @classmethod
    def aggregate_report(self, date_from, date_to):
        finished_status = Status.objects.get(slug='finished')
        circuit_status = Status.objects.get(slug='api')

        deliveries = Delivery.objects.filter(
            Q(created_at__date__lte=date_to) & 
            Q(created_at__date__gte=date_from) &
            Q(created_by__isnull=False)
        ).values('created_by__username').annotate(
            finished_deliveries=Count(
                Case(
                    When(status=finished_status, then=1),
                    output_field=models.IntegerField()
                )),
            finished_commission=Coalesce(
                Sum(
                    Case(
                        When(status=finished_status, then=F'commission'),
                        output_field=models.FloatField()
                    )),
                Value(0.0),
                ),
            circuit_deliveries=Count(
                Case(
                    When(status=circuit_status, then=1),
                    output_field=models.IntegerField()
                )),
            circuit_commission=Coalesce(
                Sum(
                    Case(
                        When(status=circuit_status, then=F'commission'),
                        output_field=models.FloatField()
                    )),
                Value(0.0),
                )
            )

        return deliveries


class Rate(models.Model):
    slug = models.CharField(verbose_name='Валютная пара', max_length=10, unique=True)
    rate = models.FloatField(verbose_name='Курс', default=0)

    class Meta:
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'
    
    def __str__(self):
        return f'{self.slug} : {self.rate}'


Units = (
    (1, '%'),
    (2, '₪')
)


class Commission(models.Model):
    value = models.FloatField(verbose_name='Размер', default=0)
    unit = models.IntegerField('Единицы измерения', choices=Units)
    low_value = models.IntegerField(verbose_name='От (в долларах)', default=0)
    high_value = models.IntegerField(verbose_name='До (в долларах)', null=True, blank=True, default=None)
    order = models.PositiveIntegerField(verbose_name='Порядок', default=0, null=True, blank=True,)

    class Meta:
        verbose_name = 'комиссия'
        verbose_name_plural = 'комиссии'
        ordering = ('order',)
    
    def __str__(self):
        symbol = '₪'
        if self.unit == 1:
            symbol = '%'

        return f'{self.value}{symbol}'


class Status(models.Model):
    slug = models.CharField(verbose_name='Слаг', max_length=10, unique=True)
    text = models.CharField(verbose_name='Описание статуса', max_length=200, unique=True)

    class Meta:
        verbose_name = 'статус'
        verbose_name_plural = 'статусы'
    
    def __str__(self):
        return self.text


@receiver(post_save, sender=Transfer)
def update_delivery_valid(sender, instance, **kwargs):
    usd_amount = 0
    commission = 0

    success_status = Status.objects.get(slug='saved')
    error_status = Status.objects.get(slug='save_error')

    delivery_total_usd_amount = instance.delivery.calculate_total_usd_amount()
    instance.delivery.total_usd = round(delivery_total_usd_amount, 2)

    for transfer in instance.delivery.transfers.all():
        usd_amount += transfer.usd_amount

        if usd_amount < 1:
            instance.delivery.valid = False
            instance.delivery.status = error_status
            instance.delivery.status_message = f'У получателя ({transfer.receiver}) слишком маленькая сумма к получению.'
            instance.delivery.save()
            break
        
        if transfer.pick_up:
            commission += 10

        if transfer.pick_up and not transfer.address:
            instance.delivery.valid = False
            instance.delivery.status = error_status
            instance.delivery.status_message = f'У получателя с доставкой ({transfer.receiver}) не указан адрес.'
            instance.delivery.save()
            break

    else:
        if usd_amount - 1 <= delivery_total_usd_amount and usd_amount + 1 >= delivery_total_usd_amount:
            instance.delivery.valid = True
            instance.delivery.commission = round(commission + instance.delivery.calculate_commission(), 2)
            
            if (instance.delivery.status_message is None) or ('Доставка передана в Circuit.' not in instance.delivery.status_message and\
            'Ошибка передачи в Circuit (необходимо вручную).' not in instance.delivery.status_message):
                instance.delivery.status = success_status
                instance.delivery.status_message = 'Доставка сохранена.'

                try:
                    delivery_to_gspread(instance.delivery)
                    gspread = True
                except Exception as ex:
                    gspread = False

                stop_id = send_pickup_address(instance.delivery.sender, instance.delivery)
                if stop_id:
                    api_status = Status.objects.get(slug='api')
                    instance.delivery.circuit_id = stop_id
                    instance.delivery.status = api_status
                    instance.delivery.status_message = 'Доставка передана в Circuit.'
                else:
                    api_error_status = Status.objects.get(slug='api_error')
                    instance.delivery.status = api_error_status
                    instance.delivery.status_message = 'Ошибка передачи в Circuit (необходимо вручную).'
                
                if not gspread:
                    instance.delivery.status_message += ' Ошибка при записи в гугл таблицу.'
                        
        else:
            instance.delivery.valid = False
            instance.delivery.status = error_status
            instance.delivery.status_message = f'Не сходится сумма долларов к отправке.'
        
        instance.delivery.save()