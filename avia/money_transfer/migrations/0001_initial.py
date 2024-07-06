# Generated by Django 4.2 on 2024-07-03 10:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=250, verbose_name='Адрес')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')),
            ],
            options={
                'verbose_name': 'адрес',
                'verbose_name_plural': 'адреса',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usd_amount', models.FloatField(default=0, verbose_name='Сумма в долларах')),
                ('ils_amount', models.FloatField(default=0, verbose_name='Сумма в шекелях')),
                ('commission', models.FloatField(default=0, help_text='Рассчитается автоматически', verbose_name='Комиссия')),
            ],
            options={
                'verbose_name': 'доставка',
                'verbose_name_plural': 'доставки',
            },
        ),
        migrations.CreateModel(
            name='Manager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_id', models.CharField(max_length=100, unique=True, verbose_name='Telegram id')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')),
            ],
            options={
                'verbose_name': 'менеджер',
                'verbose_name_plural': 'менеджеры',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.CreateModel(
            name='Receiver',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Имя')),
                ('phone', models.CharField(max_length=100, unique=True, verbose_name='Номер телефона')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')),
                ('addresses', models.ManyToManyField(blank=True, to='money_transfer.address', verbose_name='Адреса')),
            ],
            options={
                'verbose_name': 'получатель',
                'verbose_name_plural': 'получатель',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pick_up', models.BooleanField(default=False, verbose_name='Доставка до адреса')),
                ('usd_amount', models.FloatField(default=0, verbose_name='Сумма в долларах')),
                ('ils_amount', models.FloatField(default=0, verbose_name='Сумма в шекелях')),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='receivers_deliveries', to='money_transfer.address', verbose_name='Адрес получателя')),
                ('delivery', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers', to='money_transfer.delivery')),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers', to='money_transfer.receiver', verbose_name='Получатель')),
            ],
        ),
        migrations.CreateModel(
            name='Sender',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Имя')),
                ('phone', models.CharField(max_length=100, unique=True, verbose_name='Номер телефона')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')),
                ('addresses', models.ManyToManyField(blank=True, to='money_transfer.address', verbose_name='Адреса')),
            ],
            options={
                'verbose_name': 'отправитель',
                'verbose_name_plural': 'отправители',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.AddField(
            model_name='delivery',
            name='deliveries',
            field=models.ManyToManyField(related_name='deliveries', to='money_transfer.transfer', verbose_name='Параметры доставки'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='money_transfer.sender', verbose_name='Отправитель'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='sender_address',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='senders_deliveries', to='money_transfer.address', verbose_name='Адрес отправителя'),
        ),
    ]
