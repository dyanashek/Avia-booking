import json

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Count, Sum, Q, Case, When, F, Value, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError

from money_transfer.utils import send_pickup_address, delivery_to_gspread, get_delivery_ids, update_delivery_buy_rate
from errors.models import AppError
from core.utils import send_message_on_telegram
from config import TELEGRAM_BOT

User = get_user_model()


class Manager(models.Model):
    name = models.CharField(verbose_name='Имя', max_length=100, null=True, blank=True, default=None)
    telegram_id = models.CharField(verbose_name='Telegram id', max_length=100, unique=True)
    updated_at = models.DateTimeField(verbose_name='Последнее обновление', auto_now=True)
    curr_input = models.CharField(verbose_name='Текущий ввод', max_length=100, null=True, blank=True, default=None)

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
    credit = models.BooleanField(verbose_name='В кредит?', null=True, blank=True, default=None)

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


DRIVERS = (
    ('1', 'Первый водитель',),
    ('2', 'Второй водитель',),
    ('3', 'Третий водитель',),
)


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
    rate = models.FloatField(verbose_name='Курс на момент перевода', null=True, blank=True, default=None)
    driver = models.CharField(verbose_name='Водитель', max_length=50, null=True, blank=True, choices=DRIVERS)

    circuit_api = models.BooleanField(null=True, blank=True, default=None)
    gspread_api = models.BooleanField(null=True, blank=True, default=None)

    created_by_callcenter = models.BooleanField(verbose_name='Создано колл центром?', default=False)
    approved_by_client = models.BooleanField(verbose_name='Одобрено клиентом?', null=True, blank=True, default=True)
    invite_client = models.CharField(verbose_name='Ссылка для подтверждения', max_length=512, null=True, blank=True)

    class Meta:
        verbose_name = 'доставка'
        verbose_name_plural = 'доставки'

    def __str__(self):
        return f'{self.sender.name} - {self.sender.phone}'

    def save(self, *args, **kwargs) -> None:
        self.sender.addresses.add(self.sender_address)
        self.sender.save()
        if not self.rate:
            self.rate = Rate.objects.get(slug='usd-ils').rate

        super().save(*args, **kwargs)
    
    def calculate_total_usd_amount(self):
        ils_rate = Rate.objects.get(slug='usd-ils').rate
        usd_amount = self.usd_amount + self.ils_amount / ils_rate
        return usd_amount

    def calculate_commission(self):
        usd_amount = round(self.calculate_total_usd_amount(), 0)
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

    @classmethod
    def calculate_params(self, start_date, end_date):
        profit = 0

        brutto = 0
        netto = 0

        not_picked = 0
        not_provided = 0

        deliveries = Delivery.objects.filter(Q(status__slug__in=['api', 'finished']) &
                                Q(created_at__date__gte=start_date) &
                                Q(created_at__date__lte=end_date)).select_related('status').all()

        for delivery in deliveries:
            brutto += delivery.total_usd

            if delivery.status.slug == 'api':
                not_picked += delivery.total_usd

            elif delivery.status.slug == 'finished':
                profit += delivery.commission
                if delivery.rate and delivery.ils_amount > 0:
                    buy_rate = BuyRate.objects.filter(date=delivery.created_at.date()).first()
                    if buy_rate:
                        profit += (delivery.ils_amount / delivery.rate) * (delivery.rate - buy_rate.rate)

                for transfer in delivery.transfers.all():
                    if transfer.pass_date is not None:
                        netto += transfer.usd_amount
                    else:
                        not_provided += transfer.usd_amount
        
        return int(profit), int(brutto), int(netto), int(not_picked), int(not_provided)

    @classmethod
    def count_uncollected(self):
        return dict(Delivery.objects.filter(status__slug='api').aggregate(
            usd=Sum('usd_amount'),
            ils=Sum('ils_amount'),
            commission=Sum('commission'),
            total_usd=Sum('total_usd'),
        ))

    @property
    def is_error(self):
        if self.status.slug in ['save_error', 'api_error',]:
            return True
        return False

    @property
    def is_circuit(self):
        if self.status.slug == 'api':
            for transfer in self.transfers.all():
                if transfer.pass_date is None:
                    return True
        return False
    
    @property
    def is_received(self):
        if self.status.slug == 'finished':
            for transfer in self.transfers.all():
                if transfer.pass_date is None:
                    return True
        return False
    
    @property
    def is_loan(self):
        for transfer in self.transfers.all():
            if transfer.pass_date and transfer.credit:
                return True
        return False
    
    @property
    def is_finished(self):
        for transfer in self.transfers.all():
            if transfer.pass_date and (transfer.credit is False):
                return True
        return False

    @property
    def is_waiting(self):
        if self.status.slug == 'waiting':
            return True
        return False

    @property
    def is_cancelled(self):
        if self.status.slug == 'cancelled':
            return True
        return False


class Rate(models.Model):
    slug = models.CharField(verbose_name='Валютная пара', max_length=10, unique=True)
    rate = models.FloatField(verbose_name='Курс', default=0)

    class Meta:
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'
    
    def __str__(self):
        return f'{self.slug} : {self.rate}'


class BuyRate(models.Model):
    date = models.DateField(verbose_name='Дата')
    rate = models.FloatField(verbose_name='Курс', default=0)

    class Meta:
        verbose_name = 'курс покупки'
        verbose_name_plural = 'курсы покупки'
        ordering = ('-date',)
    
    def __str__(self):
        return str(self.rate)


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


class Balance(models.Model):
    debt_firms = models.FloatField(verbose_name='Задолженность перед фирмами', default=0)
    debt_ravshan = models.FloatField(verbose_name='Задолженность перед Равшаном', default=0)
    balance = models.FloatField(verbose_name='Остаток Самарканд', default=0)


Operation_types = (
    (1, 'передано фирмам'),
    (2, 'передано Равшану'),
    (3, 'получено от фирм'),
    (4, 'получено от Равшана'),
)


operation_types_dict = dict(Operation_types)
class DebitCredit(models.Model):
    amount = models.FloatField(verbose_name='Сумма в $', default=0)
    operation_type = models.IntegerField('Тип операции', choices=Operation_types)
    date = models.DateField(verbose_name='Дата')

    class Meta:
        verbose_name = 'дебит-кредит'
        verbose_name_plural = 'дебит-кредит'
        ordering = ('-date',)

    @classmethod
    def aggregate_report(self, date_from, date_to):
        data = DebitCredit.objects.filter(
            Q(date__lte=date_to) & 
            Q(date__gte=date_from)
        ).values('date', 'operation_type', 'amount').order_by('date')

        ravshan_balance = 0
        companies_balance = 0
        for item in data:
            operation_type = int(item['operation_type'])
            if operation_type == 1:
                companies_balance -= item['amount']
            elif operation_type == 2:
                ravshan_balance -= item['amount']
            elif operation_type == 3:
                companies_balance += item['amount']
            elif operation_type == 4:
                ravshan_balance += item['amount']

            item['operation_type'] = operation_types_dict.get(operation_type, 'Неизвестный тип')
        
        balance = Balance.objects.get(id=1)
        ravshan_balance_all = balance.debt_ravshan
        companies_balance_all = balance.debt_firms
        data = list(data)
        data.append({'date': '', 'operation_type': '', 'amount': ''})
        data.append({'date': 'Задолженность перед Равшаном (за период)', 'operation_type': '', 'amount': ravshan_balance})
        data.append({'date': 'Задолженность перед фирмами (за период)', 'operation_type': '', 'amount': companies_balance})
        data.append({'date': '', 'operation_type': '', 'amount': ''})
        data.append({'date': 'Задолженность перед Равшаном (текущая)', 'operation_type': '', 'amount': ravshan_balance_all})
        data.append({'date': 'Задолженность перед фирмами (текущая)', 'operation_type': '', 'amount': companies_balance_all})

        return data


class Report(models.Model):
    report_date = models.DateField(verbose_name='Дата отчета',)
    first_driver_usd = models.FloatField(verbose_name='Получено $ (первый водитель)', default=0)
    first_driver_ils = models.FloatField(verbose_name='Получено ₪ (первый водитель)', default=0)
    first_driver_commission = models.FloatField(verbose_name='Получено комиссии ₪ (первый водитель)', default=0)
    first_driver_points = models.IntegerField(verbose_name='Кол-во адресов (первый водитель)', default=0)

    second_driver_usd = models.FloatField(verbose_name='Получено $ (второй водитель)', default=0)
    second_driver_ils = models.FloatField(verbose_name='Получено ₪ (второй водитель)', default=0)
    second_driver_commission = models.FloatField(verbose_name='Получено комиссии ₪ (второй водитель)', default=0)
    second_driver_points = models.IntegerField(verbose_name='Кол-во адресов (второй водитель)', default=0)

    third_driver_usd = models.FloatField(verbose_name='Получено $ (третий водитель)', default=0)
    third_driver_ils = models.FloatField(verbose_name='Получено ₪ (третий водитель)', default=0)
    third_driver_commission = models.FloatField(verbose_name='Получено комиссии ₪ (третий водитель)', default=0)
    third_driver_points = models.IntegerField(verbose_name='Кол-во адресов (третий водитель)', default=0)

    class Meta:
        verbose_name = 'отчет'
        verbose_name_plural = 'отчеты'
        ordering = ('-report_date',)

    def __str__(self):
        return self.report_date.strftime('%d.%m.%Y')

    @property
    def total_usd(self):
        return self.first_driver_usd + self.second_driver_usd + self.third_driver_usd
    
    @property
    def total_ils(self):
        return self.first_driver_ils + self.second_driver_ils + self.third_driver_ils
    
    @property
    def total_commission(self):
        return self.first_driver_commission + self.second_driver_commission + self.third_driver_commission
    
    @property
    def total_points(self):
        return self.first_driver_points + self.second_driver_points + self.third_driver_points

    @classmethod
    def aggregate_report(self, date_from, date_to):
        first_driver = {
            'driver': 'Первый водитель',
            'usd': 0,
            'ils': 0,
            'commission': 0,
            'points': 0,
        }
        second_driver = {
            'driver': 'Второй водитель',
            'usd': 0,
            'ils': 0,
            'commission': 0,
            'points': 0,
        }
        third_driver = {
            'driver': 'Третий водитель',
            'usd': 0,
            'ils': 0,
            'commission': 0,
            'points': 0,
        }

        report_summary = Report.objects.filter(
            Q(report_date__lte=date_to) & 
            Q(report_date__gte=date_from)
        ).aggregate(
            first_driver_usd=Sum('first_driver_usd'),
            first_driver_ils=Sum('first_driver_ils'),
            first_driver_commission=Sum('first_driver_commission'),
            first_driver_points=Sum('first_driver_points'),
            second_driver_usd=Sum('second_driver_usd'),
            second_driver_ils=Sum('second_driver_ils'),
            second_driver_commission=Sum('second_driver_commission'),
            second_driver_points=Sum('second_driver_points'),
            third_driver_usd=Sum('third_driver_usd'),
            third_driver_ils=Sum('third_driver_ils'),
            third_driver_commission=Sum('third_driver_commission'),
            third_driver_points=Sum('third_driver_points'),
            )
        
        for title, value in report_summary.items():
            if 'first' in title:
                if value:
                    first_driver[title.replace('first_driver_' , '')] = value
            elif 'second' in title:
                if value:
                    second_driver[title.replace('second_driver_' , '')] = value
            elif 'third' in title:
                if value:
                    third_driver[title.replace('third_driver_' , '')] = value

        first_driver = [first_driver['driver'], first_driver['usd'], first_driver['ils'], first_driver['commission'], first_driver['points'],]
        second_driver = [second_driver['driver'], second_driver['usd'], second_driver['ils'], second_driver['commission'], second_driver['points'],]
        third_driver = [third_driver['driver'], third_driver['usd'], third_driver['ils'], third_driver['commission'], third_driver['points'],]
        return [first_driver, second_driver, third_driver]


@receiver(post_save, sender=Transfer)
def update_delivery_valid(sender, instance: Transfer, **kwargs):
    usd_amount = 0
    commission = 0

    success_status = Status.objects.get(slug='saved')
    error_status = Status.objects.get(slug='save_error')

    delivery_total_usd_amount = instance.delivery.calculate_total_usd_amount()
    instance.delivery.total_usd = round(delivery_total_usd_amount, 2)

    codes = ''

    for transfer in instance.delivery.transfers.all():
        codes += f'{transfer.id}, '
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
            
            if not instance.delivery.created_by_callcenter:
                if (instance.delivery.status_message is None) or ('Доставка передана в Circuit' not in instance.delivery.status_message and\
                'Ошибка передачи в Circuit (необходимо вручную)' not in instance.delivery.status_message and 'Получено от отправителя' not in instance.delivery.status_message):
                    instance.delivery.status = success_status
                    instance.delivery.status_message = 'Доставка сохранена.'

                    try:
                        delivery_to_gspread(instance.delivery)
                        gspread = True
                    except Exception as ex:
                        gspread = False

                        try:
                            AppError.objects.create(
                                source='5',
                                error_type='6',
                                description=f'Не удалось перенести данные в гугл таблицу (отправка денег, создание). {instance.delivery.id}. {ex}',
                            )
                        except:
                            pass

                    codes = codes.rstrip(', ')
                    stop_id = send_pickup_address(instance.delivery.sender, instance.delivery, codes)
                    if stop_id:
                        api_status = Status.objects.get(slug='api')
                        instance.delivery.circuit_id = stop_id
                        instance.delivery.circuit_api = True
                        instance.delivery.status = api_status
                        instance.delivery.status_message = 'Доставка передана в Circuit.'
                    else:
                        api_error_status = Status.objects.get(slug='api_error')
                        instance.delivery.circuit_api = False
                        instance.delivery.status = api_error_status
                        instance.delivery.status_message = 'Ошибка передачи в Circuit (необходимо вручную).'
                    
                    if not gspread:
                        instance.delivery.status_message += ' Ошибка при записи в гугл таблицу.'
                        instance.delivery.gspread_api = False
                    else:
                        instance.delivery.gspread_api = True

            else:
                if (instance.delivery.status_message is None) or ('Доставка передана в Circuit' not in instance.delivery.status_message and\
                'Ошибка передачи в Circuit (необходимо вручную)' not in instance.delivery.status_message and\
                'Получено от отправителя' not in instance.delivery.status_message and 'Ожидает подтверждения клиентом' not in instance.delivery.status_message):
                    api_status = Status.objects.get(slug='waiting')
                    instance.delivery.status = api_status
                    instance.delivery.status_message = 'Ожидает подтверждения клиентом.'

                    if instance.delivery.sender.user:
                        message = f'''
                                    \nПодтвердите информацию о переводе!\
                                    \n\
                                    \n*Отправление:*\
                                    \nНомер отправителя: *{instance.delivery.sender.phone}*\
                                    '''
                        if instance.delivery.ils_amount:
                            message += f'\nСумма в ₪: *{int(instance.delivery.ils_amount)}*'
                        
                        message += f'''\nСумма в $: *{int(instance.delivery.usd_amount)}*\
                                    \nКомиссия в ₪: *{int(instance.delivery.commission)}*\
                                    '''

                        if instance.delivery.ils_amount:     
                            message += f'\nИтого в $: *{int(instance.delivery.total_usd)}*'
                        
                        message += f'\n\n*Получатели:*'

                        for num, transfer in enumerate(instance.delivery.transfers.all()):
                            if transfer.pick_up:
                                pick_up = 'да'
                            else:
                                pick_up = 'нет'

                            transfer_message = f'''\n{num + 1}. Код получения: *{transfer.id}*\
                                                \nНомер получателя: *{transfer.receiver.phone}*\
                                                \nСумма: *{int(transfer.usd_amount)} $*\
                                                \nДоставка: *{pick_up}*\
                                                '''
                            
                            if transfer.address:
                                address = transfer.address.address
                                transfer_message += f'\nАдрес: *{address}*'
                            transfer_message += '\n'
                            message += transfer_message

                        params = {
                            'chat_id': instance.delivery.sender.user.user_id,
                            'text': message,
                            'parse_mode': 'Markdown',
                            'reply_markup': json.dumps({
                                'inline_keyboard': [
                                    [{'text': '✅', 'callback_data': f'delivery:confirm:{instance.delivery.id}'},
                                    {'text': '❌', 'callback_data': f'delivery:cancel:{instance.delivery.id}'}],
                                ]
                            })
                        }

                        response = send_message_on_telegram(params)
                        if not response or not response.ok:
                            instance.delivery.invite_client = f'https://t.me/{TELEGRAM_BOT}?start=money{instance.delivery.id}'
                        else:
                            instance.delivery.invite_client = f'отправлено: https://t.me/{TELEGRAM_BOT}?start=money{instance.delivery.id}'
                    else:
                        instance.delivery.invite_client = f'https://t.me/{TELEGRAM_BOT}?start=money{instance.delivery.id}'

        else:
            instance.delivery.valid = False
            instance.delivery.status = error_status
            instance.delivery.status_message = f'Не сходится сумма долларов к отправке.'
        
        instance.delivery.save()


@receiver(post_save, sender=BuyRate)
def update_gspread_buy_rate(sender, instance: BuyRate, created, **kwargs):
    if not created:
        ids = Delivery.objects.filter(created_at__date=instance.date).values_list('id', flat=True)
        ids = list(ids)
        
        for num, delivery_id in enumerate(get_delivery_ids()):
            if num != 0:
                try:
                    if int(delivery_id) in ids:
                        update_delivery_buy_rate(instance.rate, num + 1)        
                except Exception as ex:
                    try:
                        AppError.objects.create(
                            source='5',
                            error_type='6',
                            description=f'Не удалось перенести данные в гугл таблицу (курс покупки). {delivery_id}. {ex}',
                        )
                    except:
                        pass


@receiver(post_save, sender=Delivery)
def update_gspread_buy_rate(sender, instance: Delivery, created, **kwargs):
    if (not created and instance.approved_by_client is not None and\
    instance.created_by_callcenter and instance.circuit_id is None and\
    instance.valid):
        if instance.approved_by_client:
            if (instance.status_message is None) or ('Доставка передана в Circuit' not in instance.status_message and\
            'Ошибка передачи в Circuit (необходимо вручную)' not in instance.status_message and\
            'Получено от отправителя' not in instance.status_message and 'Отменено клиентом' not in instance.status_message):

                codes = ''
                for transfer in instance.transfers.all():
                    codes += f'{transfer.id}, '

                try:
                    delivery_to_gspread(instance)
                    gspread = True
                except Exception as ex:
                    gspread = False

                    try:
                        AppError.objects.create(
                            source='5',
                            error_type='6',
                            description=f'Не удалось перенести данные в гугл таблицу (отправка денег, создание - через подтверждение клиентом). {instance.id}. {ex}',
                        )
                    except:
                        pass

                codes = codes.rstrip(', ')
                stop_id = send_pickup_address(instance.sender, instance, codes)
                if stop_id:
                    api_status = Status.objects.get(slug='api')
                    instance.circuit_id = stop_id
                    instance.circuit_api = True
                    instance.status = api_status
                    instance.status_message = 'Доставка передана в Circuit.'
                else:
                    api_error_status = Status.objects.get(slug='api_error')
                    instance.circuit_api = False
                    instance.status = api_error_status
                    instance.status_message = 'Ошибка передачи в Circuit (необходимо вручную).'
                
                if not gspread:
                    instance.status_message += ' Ошибка при записи в гугл таблицу.'
                    instance.gspread_api = False
                else:
                    instance.gspread_api = True

                instance.save()

        elif 'Отменено клиентом' not in instance.status_message:
            api_status = Status.objects.get(slug='cancelled')
            instance.status = api_status
            instance.status_message = 'Отменено клиентом'
            instance.save(update_fields=['status', 'status_message'])
