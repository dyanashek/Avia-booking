# Generated by Django 4.2 on 2025-03-29 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_basesettings_delivery_price_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='buyerprofile',
            name='icount_id',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID в iCount'),
        ),
    ]
