# Generated by Django 4.2 on 2024-10-28 09:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='operation',
            options={'ordering': ('date',), 'verbose_name': 'операция', 'verbose_name_plural': 'операции'},
        ),
        migrations.AlterField(
            model_name='contractor',
            name='agent_type',
            field=models.CharField(choices=[('1', 'переводит usdt'), ('2', 'получает usdt')], max_length=30, verbose_name='Тип контрагента'),
        ),
        migrations.AlterField(
            model_name='operation',
            name='operation_type',
            field=models.CharField(choices=[('1', 'получение usdt от контрагента'), ('2', 'передача шекелей контрагенту'), ('3', 'получение usd от контрагента'), ('4', 'передача usdt контрагенту')], help_text='Выбранный контрагент должен соответствовать указанному типу операции', max_length=50, verbose_name='Тип операции'),
        ),
    ]