# Generated by Django 4.2 on 2024-07-31 04:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0022_manager_name'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='transfer',
            options={'verbose_name': 'перевод', 'verbose_name_plural': 'переводы'},
        ),
    ]