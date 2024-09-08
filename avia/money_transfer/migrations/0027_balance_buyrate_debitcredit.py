# Generated by Django 4.2 on 2024-08-13 05:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0026_manager_curr_input'),
    ]

    operations = [
        migrations.CreateModel(
            name='Balance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('debt_firms', models.FloatField(default=0, verbose_name='Задолженность перед фирмами')),
                ('debt_ravshan', models.FloatField(default=0, verbose_name='Задолженность перед Равшаном')),
                ('balance', models.FloatField(default=0, verbose_name='Остаток Самарканд')),
            ],
        ),
        migrations.CreateModel(
            name='BuyRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата')),
                ('rate', models.FloatField(default=0, verbose_name='Курс')),
            ],
            options={
                'verbose_name': 'курс покупки',
                'verbose_name_plural': 'курсы покупки',
            },
        ),
        migrations.CreateModel(
            name='DebitCredit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(default=0, verbose_name='Сумма в $')),
                ('operation_type', models.IntegerField(choices=[(1, 'передано фирмам'), (2, 'передано Равшану'), (3, 'получено от фирм'), (4, 'получено от Равшана')], verbose_name='Тип операции')),
                ('date', models.DateField(verbose_name='Дата')),
            ],
        ),
    ]