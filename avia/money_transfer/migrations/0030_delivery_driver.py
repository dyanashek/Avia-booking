# Generated by Django 4.2 on 2024-09-08 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('money_transfer', '0029_report_alter_debitcredit_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='driver',
            field=models.CharField(blank=True, choices=[('1', 'Первый водитель'), ('2', 'Второй водитель'), ('3', 'Третий водитель')], max_length=50, null=True, verbose_name='Водитель'),
        ),
    ]