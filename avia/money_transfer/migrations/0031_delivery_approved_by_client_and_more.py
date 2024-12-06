# Generated by Django 4.2 on 2024-12-06 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0030_delivery_driver'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='approved_by_client',
            field=models.BooleanField(blank=True, default=True, null=True, verbose_name='Одобрено клиентом?'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='created_by_callcenter',
            field=models.BooleanField(default=False, verbose_name='Создано колл центром?'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='invite_client',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='Ссылка для подтверждения'),
        ),
    ]
