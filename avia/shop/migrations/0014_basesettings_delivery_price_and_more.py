# Generated by Django 4.2 on 2025-03-24 06:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0013_accesstoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='basesettings',
            name='delivery_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Стоимость доставки'),
        ),
        migrations.AddField(
            model_name='basesettings',
            name='free_delivery',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Бесплатная доставка от'),
        ),
        migrations.AddField(
            model_name='order',
            name='circuit_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID circuit'),
        ),
        migrations.AddField(
            model_name='order',
            name='circuit_success',
            field=models.BooleanField(blank=True, default=None, null=True, verbose_name='Доставка прошла?'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Стоимость доставки'),
        ),
    ]
