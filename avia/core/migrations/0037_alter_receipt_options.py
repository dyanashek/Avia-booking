# Generated by Django 4.2 on 2024-09-23 10:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_receipt'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='receipt',
            options={'ordering': ('-notify_time',), 'verbose_name': 'квитанция', 'verbose_name_plural': 'квитанции'},
        ),
    ]
