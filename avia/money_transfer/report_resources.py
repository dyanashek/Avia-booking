import datetime

from django.contrib.auth import get_user_model
from import_export import resources
from import_export.fields import Field

from money_transfer.models import Delivery, BuyRate


class DeliveryResource(resources.ModelResource):
    created_at_field = Field(column_name='Дата создания')
    received_at_field = Field(column_name='Дата получения')
    receive_codes = Field(column_name='Коды получения')
    receivers_count = Field(column_name='Количество получателей')
    approved_field = Field(column_name='Одобрено клиентом?')
    receiver_names = Field(column_name='Имена получателей')
    receiver_phones = Field(column_name='Телефоны получателей')
    receiver_addresses = Field(column_name='Адреса получателей')
    receivers_delivery = Field(column_name='Доставка до адреса')
    receivers_amount = Field(column_name='Сумма для получателей ($)')
    receivers_receive_date = Field(column_name='Дата получения получателями')
    receivers_credit = Field(column_name='В кредит?')
    buy_rate = Field(column_name='Курс покупки')
    driver_field = Field(column_name='Водитель')

    def __init__(self, **kwargs):
        super().__init__()
        self.date_from = kwargs.get('date_from')
        self.date_to = kwargs.get('date_to')
        self.author = kwargs.get('author')

    class Meta:
        model = Delivery
        fields = ('id', 'created_at_field', 'received_at_field', 'drivers_comment', 'status__text', 'driver_field', 'receive_codes', 'sender__name',
                  'sender_address__address', 'sender__phone', 'usd_amount', 'ils_amount', 'commission', 'rate', 'approved_field', 'receivers_count',
                  'receiver_names', 'receiver_phones', 'receiver_addresses', 'receivers_delivery', 'receivers_amount',
                  'receivers_receive_date', 'receivers_credit', 'buy_rate',
                  )
    
    def filter_export(self, queryset, **kwargs):
        if self.author:
            author = get_user_model().objects.filter(username=self.author).first()
        else:
            author = None
        
        if self.date_from:
            queryset = queryset.filter(created_at__date__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(created_at__date__lte=self.date_to)
        if author:
            queryset = queryset.filter(created_by=author)

        return queryset.order_by('created_at')
    
    def get_export_headers(self, selected_fields=None):
        headers = super().get_export_headers(selected_fields=selected_fields)
        for i, h in enumerate(headers):
            if h == 'id':
                headers[i] = "ID"
            elif h == 'drivers_comment':
                headers[i] = "Комментарий водителя"
            elif h == 'sender__name':
                headers[i] = "Отправитель"
            elif h == 'sender_address__address':
                headers[i] = "Адрес отправителя"
            elif h == 'sender__phone':
                headers[i] = "Телефон отправителя"
            elif h == 'usd_amount':
                headers[i] = "Сумма в $"
            elif h == 'ils_amount':
                headers[i] = "Сумма в ₪"
            elif h == 'commission':
                headers[i] = "Комиссия в ₪"
            elif h == 'rate':
                headers[i] = "Курс на момент перевода"
            elif h == 'status__text':
                headers[i] = "Статус"
            elif h == 'driver':
                headers[i] = "Водитель"
            
        return headers

    def dehydrate_created_at_field(self, obj):
        if obj.created_at:
            return (obj.created_at + datetime.timedelta(hours=3)).strftime('%d.%m.%Y %H:%M')
        return '-'

    def dehydrate_received_at_field(self, obj):
        if obj.received_at:
            return (obj.received_at + datetime.timedelta(hours=3)).strftime('%d.%m.%Y %H:%M')
        return '-'

    def dehydrate_receive_codes(self, obj):
        codes = []
        for transfer in obj.transfers.all():
            codes.append(str(transfer.id))
        return ', '.join(codes)

    def dehydrate_receivers_count(self, obj):
        return obj.transfers.count()

    def dehydrate_receiver_names(self, obj):
        names = []
        for transfer in obj.transfers.all():
            names.append(transfer.receiver.name)
        return ', '.join(names)

    def dehydrate_receiver_phones(self, obj):
        phones = []
        for transfer in obj.transfers.all():
            phones.append(transfer.receiver.phone)
        return ', '.join(phones)
    
    def dehydrate_receiver_addresses(self, obj):
        addresses = []
        for transfer in obj.transfers.all():
            if transfer.address:
                addresses.append(transfer.address.address)
            else:
                addresses.append('-')
        return ', '.join(addresses)
    
    def dehydrate_receivers_delivery(self, obj):
        delivery = []
        for transfer in obj.transfers.all():
            if transfer.pick_up:
                delivery.append('Да')
            else:
                delivery.append('Нет')
        return ', '.join(delivery)
    
    def dehydrate_receivers_amount(self, obj):
        amount = []
        for transfer in obj.transfers.all():
            amount.append(str(transfer.usd_amount))
        return ', '.join(amount)

    def dehydrate_receivers_receive_date(self, obj):
        receive_date = []
        for transfer in obj.transfers.all():
            if transfer.pass_date:
                receive_date.append((transfer.pass_date + datetime.timedelta(hours=3)).strftime('%d.%m.%Y %H:%M'))
            else:
                receive_date.append('-')
        return ', '.join(receive_date)

    def dehydrate_receivers_credit(self, obj):
        credit = []
        for transfer in obj.transfers.all():
            if transfer.credit:
                credit.append('Да')
            else:
                credit.append('Нет')
        return ', '.join(credit)
    
    def dehydrate_buy_rate(self, obj):
        buy_rates = []
        for transfer in obj.transfers.all():
            if transfer.pass_date:
                rate_date = (transfer.pass_date + datetime.timedelta(hours=3)).date()
                buy_rate = BuyRate.objects.filter(date=rate_date).first()
                if buy_rate:
                    buy_rates.append(str(buy_rate.rate))
                else:
                    buy_rates.append('?')
            else:
                buy_rates.append('-')
        return ', '.join(buy_rates)

    def dehydrate_approved_field(self, obj):
        if obj.approved_by_client:
            return 'Да'
        else:
            return 'Нет'
    
    def dehydrate_driver_field(self, obj):
        if obj.driver:
            if obj.driver == '1':
                return 'Первый водитель'
            elif obj.driver == '2':
                return 'Второй водитель'
            elif obj.driver == '3':
                return 'Третий водитель'
        else:
            return '-'
