from django.db import models


class Driver(models.Model):
    name = models.CharField(verbose_name='Имя', max_length=50)
    telegram_id = models.CharField(verbose_name='Telegram id', max_length=50, unique=True)
    circuit_id = models.CharField(verbose_name='Circuit id', max_length=100, unique=True)
    curr_input = models.CharField(verbose_name='Текущий ввод', max_length=100, null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'водитель'
        verbose_name_plural = 'водители'
        ordering = ('pk',)
    
    def __str__(self):
        return self.name

