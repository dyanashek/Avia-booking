# Generated by Django 4.2 on 2024-06-25 09:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_parcel_family_name_parcel_name'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='day',
            options={'ordering': ('day',), 'verbose_name': 'число', 'verbose_name_plural': 'числа'},
        ),
        migrations.AlterField(
            model_name='parcelvariation',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Вариант посылки'),
        ),
    ]
