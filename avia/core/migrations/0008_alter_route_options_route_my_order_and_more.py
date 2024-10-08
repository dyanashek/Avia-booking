# Generated by Django 4.2 on 2024-06-29 04:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_parcel_items_list'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='route',
            options={'ordering': ('my_order',), 'verbose_name': 'маршрут', 'verbose_name_plural': 'маршруты'},
        ),
        migrations.AddField(
            model_name='route',
            name='my_order',
            field=models.PositiveIntegerField(default=0, verbose_name='Порядок'),
        ),
        migrations.AlterField(
            model_name='language',
            name='my_order',
            field=models.PositiveIntegerField(default=0, verbose_name='Порядок'),
        ),
    ]
