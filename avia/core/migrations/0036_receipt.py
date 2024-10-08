# Generated by Django 4.2 on 2024-09-23 07:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_flight_lat_flight_lon_parcel_lat_parcel_lon'),
    ]

    operations = [
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link', models.URLField(verbose_name='Ссылка')),
                ('notify_time', models.DateTimeField(help_text='Указывается в UTC (-3 от МСК).', verbose_name='Время отправки')),
                ('success', models.BooleanField(blank=True, default=None, null=True, verbose_name='Успешно?')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='core.tguser', verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'уведомление пользователей',
                'verbose_name_plural': 'уведомления пользователей',
                'ordering': ('-notify_time',),
            },
        ),
    ]
