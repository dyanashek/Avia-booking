# Generated by Django 4.2 on 2025-03-31 10:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shop', '0021_order_driver_comment_topuprequest_driver_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Сумма')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Время создания')),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_transactions_receive', to=settings.AUTH_USER_MODEL, verbose_name='Получатель')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_transactions_send', to=settings.AUTH_USER_MODEL, verbose_name='Отправитель')),
            ],
            options={
                'verbose_name': 'Транзакция баланса',
                'verbose_name_plural': 'Транзакции баланса',
            },
        ),
    ]
