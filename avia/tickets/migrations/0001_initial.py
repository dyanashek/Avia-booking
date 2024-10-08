# Generated by Django 4.2 on 2024-08-08 12:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import filer.fields.image


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0031_userssim_circuit_api_userssim_circuit_api_collect_and_more'),
        migrations.swappable_dependency(settings.FILER_IMAGE_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('oneway', 'В одну сторону'), ('roundtrip', 'Туда-обратно')], max_length=15, verbose_name='Тип перелета')),
                ('phone', models.CharField(blank=True, max_length=25, null=True, verbose_name='Номер телефона')),
                ('name', models.CharField(max_length=100, verbose_name='Имя')),
                ('family_name', models.CharField(max_length=100, verbose_name='Фамилия')),
                ('address', models.CharField(blank=True, max_length=4096, null=True, verbose_name='Адрес')),
                ('sex', models.CharField(choices=[('M', 'Мужской'), ('F', 'Женский')], max_length=4096, verbose_name='Пол')),
                ('birth_date', models.DateField(verbose_name='Дата рождения')),
                ('start_date', models.DateField(verbose_name='Дата выдачи паспорта')),
                ('end_date', models.DateField(verbose_name='Дата окончания срока действия паспорта')),
                ('passport_number', models.CharField(max_length=20, verbose_name='Номер паспорта')),
                ('complete', models.BooleanField(blank=True, default=None, null=True, verbose_name='Заявка подтверждена пользователем')),
                ('price', models.FloatField(default=0, verbose_name='Стоимость в шекелях')),
                ('circuit_id', models.CharField(blank=True, max_length=250, null=True, unique=True, verbose_name='Circuit id')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('valid', models.BooleanField(default=True)),
                ('circuit_api', models.BooleanField(default=False)),
                ('arrival_date', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='arrival_flights', to='core.day', verbose_name='Дата прилета')),
                ('departure_date', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='departure_flights', to='core.day', verbose_name='Дата отлета')),
                ('passport_photo_flight', filer.fields.image.FilerImageField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.FILER_IMAGE_MODEL, verbose_name='Фото паспорта')),
                ('route', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_flights', to='core.route', verbose_name='Маршрут')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_flights', to='core.tguser', verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'билет',
                'verbose_name_plural': 'билеты',
                'ordering': ('-created_at',),
            },
        ),
    ]
