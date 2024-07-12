# Generated by Django 4.2 on 2024-07-12 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_simfare_userssim'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='simfare',
            options={'ordering': ('my_order',), 'verbose_name': 'тариф симки', 'verbose_name_plural': 'тарифы симок'},
        ),
        migrations.AlterModelOptions(
            name='userssim',
            options={'ordering': ('-created_at',), 'verbose_name': 'сим карта', 'verbose_name_plural': 'сим карты'},
        ),
        migrations.AddField(
            model_name='userssim',
            name='notified',
            field=models.BooleanField(default=False, verbose_name='Уведомлен сегодня'),
        ),
        migrations.AlterField(
            model_name='userssim',
            name='circuit_id',
            field=models.CharField(blank=True, help_text='После получения денег - удалить.', max_length=250, null=True, unique=True, verbose_name='Circuit id'),
        ),
        migrations.AlterField(
            model_name='userssim',
            name='debt',
            field=models.FloatField(help_text='Отрицательная, при оплате наперед. Изменить вручную после получения денег.', verbose_name='Задолженность'),
        ),
        migrations.AlterField(
            model_name='userssim',
            name='pay_date',
            field=models.DateField(blank=True, help_text='После получения денег - удалить.', null=True, verbose_name='Планируемая дата оплаты'),
        ),
        migrations.AlterField(
            model_name='userssim',
            name='ready_to_pay',
            field=models.BooleanField(default=False, verbose_name='Готов оплачивать'),
        ),
    ]
