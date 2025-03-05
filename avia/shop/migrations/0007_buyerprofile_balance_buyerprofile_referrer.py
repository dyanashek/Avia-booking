# Generated by Django 4.2 on 2025-02-24 08:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0006_buyerprofile_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='buyerprofile',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Баланс'),
        ),
        migrations.AddField(
            model_name='buyerprofile',
            name='referrer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to='shop.buyerprofile', verbose_name='Реферал'),
        ),
    ]
