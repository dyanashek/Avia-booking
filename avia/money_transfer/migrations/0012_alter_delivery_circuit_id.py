# Generated by Django 4.2 on 2024-07-09 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0011_delivery_circuit_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='circuit_id',
            field=models.CharField(blank=True, max_length=250, null=True, unique=True, verbose_name='Circuit id'),
        ),
    ]