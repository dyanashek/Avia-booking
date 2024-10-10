from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.db import models

from core.models import SimFare, UsersSim
from money_transfer.models import DRIVERS
from sim.utils import create_icount_client, extract_digits


User = get_user_model()


class SimCard(models.Model):
    name = models.CharField(verbose_name='Имя', max_length=512, null=True, blank=True)
    sim_phone = models.CharField(verbose_name='Номер телефона', max_length=25, unique=True)
    fare = models.ForeignKey(SimFare, verbose_name='Тариф', on_delete=models.CASCADE, related_name='admins_sims', null=True, blank=True)
    created_at = models.DateField(verbose_name='Дата приобретения', auto_now_add=True)
    next_payment = models.DateField(verbose_name='Дата следующего платежа')
    debt = models.FloatField(verbose_name='Задолженность', help_text='Отрицательная, при оплате наперед.')
    icount_id = models.IntegerField(null=True, blank=True, default=None)
    to_main_bot = models.BooleanField(verbose_name='Перенесена в основного бота?', default=False)
    created_by = models.ForeignKey(User, verbose_name='Менеджер', related_name='admin_sims', on_delete=models.SET_NULL, null=True, blank=True)
    is_stopped = models.BooleanField(verbose_name='Приостановлен', default=False)

    icount_api = models.BooleanField(verbose_name='Аккаунт в icount', null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'сим карта'
        verbose_name_plural = 'сим карты'
        ordering = ('-created_at',)
    
    def __str__(self):
        return self.sim_phone
    
    def save(self, *args, **kwargs) -> None:
        self.sim_phone = extract_digits(self.sim_phone)
        if self.id is None and self.icount_api is None and self.name:
            icount_id = create_icount_client(self.name, self.sim_phone)
            if icount_id:
                self.icount_id = icount_id
                self.icount_api = True
            else:
                self.icount_api = False
        elif self.name is None:
            self.icount_api = False

        super().save(*args, **kwargs)
    
    @classmethod
    def aggregate_report(self, date_from, date_to):
        sim_cards = SimCard.objects.filter(
            Q(created_at__lte=date_to) & 
            Q(created_at__gte=date_from) &
            Q(created_by__isnull=False) &
            Q(icount_api=True) &
            Q(to_main_bot=True)
        ).values('created_by__username').annotate(
            sims_total=Count('id'),
            sims_fares_sum=Sum('fare__price'),
            )

        return sim_cards


class Collect(models.Model):
    sim = models.ForeignKey(UsersSim, verbose_name='Симкарта', on_delete=models.CASCADE, related_name='collects')
    created_at = models.DateField(verbose_name='Дата приобретения', auto_now_add=True)
    amount = models.FloatField(verbose_name='Сумма', null=True, blank=True, default=None)
    driver = models.CharField(verbose_name='Водитель', max_length=50, choices=DRIVERS)

    class Meta:
        verbose_name = 'сбор за симкарту'
        verbose_name_plural = 'сборы за симкарты'
        ordering = ('-created_at',)
    
    def __str__(self):
        if self.sim.sim_phone:
            return self.sim.sim_phone
        return self.driver


class Report(models.Model):
    report_date = models.DateField(verbose_name='Дата отчета',)
    first_driver_ils = models.FloatField(verbose_name='Получено ₪ (первый водитель)', default=0)
    first_driver_points = models.IntegerField(verbose_name='Кол-во адресов (первый водитель)', default=0)

    second_driver_ils = models.FloatField(verbose_name='Получено ₪ (второй водитель)', default=0)
    second_driver_points = models.IntegerField(verbose_name='Кол-во адресов (второй водитель)', default=0)

    third_driver_ils = models.FloatField(verbose_name='Получено ₪ (третий водитель)', default=0)
    third_driver_points = models.IntegerField(verbose_name='Кол-во адресов (третий водитель)', default=0)

    class Meta:
        verbose_name = 'отчет'
        verbose_name_plural = 'отчеты'
        ordering = ('-report_date',)

    def __str__(self):
        return self.report_date.strftime('%d.%m.%Y')
    
    @property
    def total_ils(self):
        return self.first_driver_ils + self.second_driver_ils + self.third_driver_ils
    
    @property
    def total_points(self):
        return self.first_driver_points + self.second_driver_points + self.third_driver_points

    @classmethod
    def aggregate_report(self, date_from, date_to):
        first_driver = {
            'driver': 'Первый водитель',
            'ils': 0,
            'points': 0,
        }
        second_driver = {
            'driver': 'Второй водитель',
            'ils': 0,
            'points': 0,
        }
        third_driver = {
            'driver': 'Третий водитель',
            'ils': 0,
            'points': 0,
        }

        report_summary = Report.objects.filter(
            Q(report_date__lte=date_to) & 
            Q(report_date__gte=date_from)
        ).aggregate(
            first_driver_ils=Sum('first_driver_ils'),
            first_driver_points=Sum('first_driver_points'),
            second_driver_ils=Sum('second_driver_ils'),
            second_driver_points=Sum('second_driver_points'),
            third_driver_ils=Sum('third_driver_ils'),
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

        first_driver = [first_driver['driver'], first_driver['ils'], first_driver['points'],]
        second_driver = [second_driver['driver'], second_driver['ils'], second_driver['points'],]
        third_driver = [third_driver['driver'], third_driver['ils'], third_driver['points'],]
        return [first_driver, second_driver, third_driver]
