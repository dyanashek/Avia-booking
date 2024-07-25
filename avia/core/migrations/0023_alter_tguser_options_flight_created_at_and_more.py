# Generated by Django 4.2 on 2024-07-15 04:45

import datetime
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_alter_notification_notify_time'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tguser',
            options={'ordering': ('-created_at',), 'verbose_name': 'клиент', 'verbose_name_plural': 'Клиенты'},
        ),
        migrations.AddField(
            model_name='flight',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата приобретения'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='parcel',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2024, 7, 15, 4, 45, 8, 566897), verbose_name='Дата приобретения'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tguser',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата приобретения'),
            preserve_default=False,
        ),
    ]