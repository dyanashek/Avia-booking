# Generated by Django 4.2 on 2024-06-25 09:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_tgtext_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='parcel',
            name='family_name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Фамилия'),
        ),
        migrations.AddField(
            model_name='parcel',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Имя'),
        ),
    ]
