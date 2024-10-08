# Generated by Django 4.2 on 2024-07-04 06:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0007_commission_rate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commission',
            name='high_value',
            field=models.IntegerField(default=0, verbose_name='До (в долларах)'),
        ),
        migrations.AlterField(
            model_name='commission',
            name='low_value',
            field=models.IntegerField(default=0, verbose_name='От (в долларах)'),
        ),
        migrations.AlterField(
            model_name='commission',
            name='unit',
            field=models.IntegerField(choices=[(1, '%'), (2, '₪')], verbose_name='Единицы измерения'),
        ),
    ]
