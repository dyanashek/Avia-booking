from django.db.models import Q
from django.db import models
from decimal import Decimal

CONTRACTOR_TYPES = (
    ('1', 'переводит usdt'),
    ('2', 'получает usdt')
)


class Contractor(models.Model):
    name = models.CharField(verbose_name='Имя', max_length=50)
    agent_type = models.CharField(verbose_name='Тип контрагента', choices=CONTRACTOR_TYPES, max_length=30)
    commission = models.DecimalField(verbose_name='Комиссия агента', max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text='указывается в %')
    debt = models.DecimalField(verbose_name='Задолженность перед контрагентом', max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'контрагент'
        verbose_name_plural = 'контрагенты'
    
    def __str__(self):
        return self.name


OPERATION_TYPES = (
    ('1', 'получение usdt от контрагента'),
    ('2', 'передача шекелей контрагенту'),
    ('3', 'получение usd от контрагента'),
    ('4', 'передача usdt контрагенту')
)
operation_types_dict = dict(OPERATION_TYPES)


class Operation(models.Model):
    contractor = models.ForeignKey(Contractor, verbose_name='Контрагент', on_delete=models.CASCADE, related_name='operations')
    operation_type = models.CharField(verbose_name='Тип операции', choices=OPERATION_TYPES, max_length=50, help_text='Выбранный контрагент должен соответствовать указанному типу операции')
    amount = models.DecimalField(verbose_name='Сумма операции', max_digits=10, decimal_places=2)
    rate = models.DecimalField(verbose_name='Курс ₪/$', max_digits=10, decimal_places=2, help_text='Указывается только для операций получения usdt от контрагента, в остальных случаях будет проигнорирован', default=Decimal('0.00'))
    commission = models.DecimalField(verbose_name='Комиссия агента', max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text='указывается в %')
    date = models.DateField(verbose_name='Дата проведения операции')
    valid = models.BooleanField(verbose_name='Операция валидна?', default=False)

    class Meta:
        verbose_name = 'операция'
        verbose_name_plural = 'операции'
        ordering = ('date',)
    
    def __str__(self):
        return str(self.contractor)

    def save(self, *args, **kwargs) -> None:
        self.commission = self.contractor.commission

        if self.contractor.agent_type == '1' and self.operation_type == '1' and self.rate == Decimal('0'):
            pass
        elif ((self.contractor.agent_type == '1' and self.operation_type in ['1', '2']) or 
              (self.contractor.agent_type == '2' and self.operation_type in ['3', '4'])):

            if self.id is None or self.valid is False:
                if self.operation_type == '1':
                    self.contractor.debt += self.amount * self.rate * (Decimal('1') + self.commission / Decimal('100'))
                elif self.operation_type == '2':
                    self.contractor.debt -= self.amount
                elif self.operation_type == '3':
                    self.contractor.debt += self.amount / (Decimal('1') + self.commission / Decimal('100'))
                elif self.operation_type == '4':
                    self.contractor.debt -= self.amount
                self.contractor.save()

            self.valid = True

        super().save(*args, **kwargs)

    @classmethod
    def aggregate_report(self, date_from, date_to):
        data = Operation.objects.filter(
            Q(date__lte=date_to) & 
            Q(date__gte=date_from) &
            Q(valid=True)
        ).values('date', 'contractor', 'operation_type', 'amount', 'valid', 'rate', 'commission').order_by('date')

        for item in data:
            operation_type = item['operation_type']
            if item['operation_type'] != '1':
                item['rate'] = '-'
            
            if item['operation_type'] == '1':
                item['valid'] = 'usdt'
            elif item['operation_type'] == '2':
                item['valid'] = '₪'
            elif item['operation_type'] == '3':
                item['valid'] = '$'
            elif item['operation_type'] == '4':
                item['valid'] = 'usdt'

            item['commission'] =  f"{item['commission']}%"
            item['contractor'] = Contractor.objects.get(id=item['contractor']).name
            item['operation_type'] = operation_types_dict.get(operation_type, 'Неизвестный тип')
        
        data = list(data)
        data.append({'date': '', 'contractor': '', 'operation_type': '', 'amount': '', 'valid': '', 'rate': '', 'commission': ''})
        for contractor in Contractor.objects.all().order_by('agent_type'):
            debt = contractor.debt
            if contractor.agent_type == '1':
                currency = '₪'
            elif contractor.agent_type == '2':
                if contractor.debt >= 0:
                    currency = 'usdt'
                else:
                    currency = '$'
                    debt = round(contractor.debt * (1 + contractor.commission / 100), 2)

            data.append({'date': 'Текущая задолженность перед', 'contractor': contractor.name, 'operation_type': '', 'amount': '', 'valid': '', 'rate': debt, 'commission': currency})

        return data