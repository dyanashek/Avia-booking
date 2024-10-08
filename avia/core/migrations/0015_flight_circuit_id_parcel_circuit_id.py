# Generated by Django 4.2 on 2024-07-09 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_remove_flight_finished_remove_parcel_finished'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='circuit_id',
            field=models.CharField(blank=True, max_length=250, null=True, unique=True, verbose_name='Circuit id'),
        ),
        migrations.AddField(
            model_name='parcel',
            name='circuit_id',
            field=models.CharField(blank=True, max_length=250, null=True, unique=True, verbose_name='Circuit id'),
        ),
    ]
