# Generated by Django 4.2 on 2024-07-04 03:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0003_delivery_valid'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='status_message',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='Статус заказа'),
        ),
    ]
