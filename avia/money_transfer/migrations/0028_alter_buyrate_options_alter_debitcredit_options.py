# Generated by Django 4.2 on 2024-08-28 14:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0027_balance_buyrate_debitcredit'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='buyrate',
            options={'ordering': ('-date',), 'verbose_name': 'курс покупки', 'verbose_name_plural': 'курсы покупки'},
        ),
        migrations.AlterModelOptions(
            name='debitcredit',
            options={'ordering': ('date',), 'verbose_name': 'дебит-кредит', 'verbose_name_plural': 'дебит-кредит'},
        ),
    ]
