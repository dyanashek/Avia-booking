# Generated by Django 4.2 on 2024-09-23 04:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sim', '0002_simcard_is_stopped_alter_simcard_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simcard',
            name='icount_api',
            field=models.BooleanField(blank=True, default=None, null=True, verbose_name='Аккаунт в icount'),
        ),
    ]
