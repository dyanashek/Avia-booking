# Generated by Django 4.2 on 2024-10-28 09:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contractor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Имя')),
                ('agent_type', models.CharField(choices=[(1, 'переводит usdt'), (2, 'получает usdt')], max_length=30, verbose_name='Тип контрагента')),
                ('commission', models.FloatField(default=0, help_text='указывается в %', verbose_name='Комиссия агента')),
                ('debt', models.FloatField(default=0, verbose_name='Задолженность перед контрагентом')),
            ],
            options={
                'verbose_name': 'контрагент',
                'verbose_name_plural': 'контрагенты',
            },
        ),
        migrations.CreateModel(
            name='Operation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operation_type', models.CharField(choices=[(1, 'получение usdt от контрагента'), (2, 'передача шекелей контрагенту'), (3, 'получение usd от контрагента'), (4, 'передача usdt контрагенту')], help_text='Выбранный контрагент должен соответствовать указанному типу операции', max_length=50, verbose_name='Тип операции')),
                ('amount', models.FloatField(verbose_name='Сумма операции')),
                ('rate', models.FloatField(default=0, help_text='Указывается только для операций получения usdt от контрагента, в остальных случаях будет проигнорирован', verbose_name='Курс ₪/$')),
                ('commission', models.FloatField(default=0, help_text='указывается в %', verbose_name='Комиссия агента')),
                ('date', models.DateField(verbose_name='Дата проведения операции')),
                ('valid', models.BooleanField(default=False, verbose_name='Операция валидна?')),
                ('contractor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operations', to='currency.contractor', verbose_name='Контрагент')),
            ],
            options={
                'verbose_name': 'контрагент',
                'verbose_name_plural': 'контрагенты',
                'ordering': ('date',),
            },
        ),
    ]
