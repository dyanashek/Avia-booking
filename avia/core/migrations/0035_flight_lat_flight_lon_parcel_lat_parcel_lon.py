# Generated by Django 4.2 on 2024-09-23 06:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_tguser_lat_tguser_lon'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='lat',
            field=models.FloatField(blank=True, default=None, null=True, verbose_name='Широта'),
        ),
        migrations.AddField(
            model_name='flight',
            name='lon',
            field=models.FloatField(blank=True, default=None, null=True, verbose_name='Долгота'),
        ),
        migrations.AddField(
            model_name='parcel',
            name='lat',
            field=models.FloatField(blank=True, default=None, null=True, verbose_name='Широта'),
        ),
        migrations.AddField(
            model_name='parcel',
            name='lon',
            field=models.FloatField(blank=True, default=None, null=True, verbose_name='Долгота'),
        ),
    ]