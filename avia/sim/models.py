from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.db import models

from core.models import SimFare
from sim.utils import create_icount_client, extract_digits


User = get_user_model()


class SimCard(models.Model):
    name = models.CharField(verbose_name='Имя', max_length=512)
    sim_phone = models.CharField(verbose_name='Номер телефона', max_length=25, unique=True)
    fare = models.ForeignKey(SimFare, verbose_name='Тариф', on_delete=models.CASCADE, related_name='admins_sims', null=True, blank=True)
    created_at = models.DateField(verbose_name='Дата приобретения', auto_now_add=True)
    next_payment = models.DateField(verbose_name='Дата следующего платежа')
    debt = models.FloatField(verbose_name='Задолженность', help_text='Отрицательная, при оплате наперед.')
    icount_id = models.IntegerField(null=True, blank=True, default=None)
    to_main_bot = models.BooleanField(verbose_name='Перенесена в основного бота?', default=False)
    created_by = models.ForeignKey(User, verbose_name='Менеджер', related_name='admin_sims', on_delete=models.SET_NULL, null=True, blank=True)

    icount_api = models.BooleanField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'сим карта'
        verbose_name_plural = 'сим карты'
        ordering = ('-created_at',)
    
    def __str__(self):
        return self.sim_phone
    
    def save(self, *args, **kwargs) -> None:
        self.sim_phone = extract_digits(self.sim_phone)
        if self.id is None:
            icount_id = create_icount_client(self.name, self.sim_phone)
            if icount_id:
                self.icount_id = icount_id
                self.icount_api = True
            else:
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