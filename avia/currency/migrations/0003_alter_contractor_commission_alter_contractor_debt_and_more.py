# Generated by Django 4.2 on 2024-10-28 09:56

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0002_alter_operation_options_alter_contractor_agent_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contractor',
            name='commission',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='указывается в %', max_digits=5, verbose_name='Комиссия агента'),
        ),
        migrations.AlterField(
            model_name='contractor',
            name='debt',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Задолженность перед контрагентом'),
        ),
        migrations.AlterField(
            model_name='operation',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма операции'),
        ),
        migrations.AlterField(
            model_name='operation',
            name='commission',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='указывается в %', max_digits=5, verbose_name='Комиссия агента'),
        ),
        migrations.AlterField(
            model_name='operation',
            name='rate',
            field=models.DecimalField(decimal_places=4, default=Decimal('0.00'), help_text='Указывается только для операций получения usdt от контрагента, в остальных случаях будет проигнорирован', max_digits=10, verbose_name='Курс ₪/$'),
        ),
    ]
