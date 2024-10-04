# Generated by Django 4.2 on 2024-10-04 09:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_delete_apperror'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(blank=True, null=True, verbose_name='Текст')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='stupid_messages', to='core.tguser', verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'сообщение от пользователя',
                'verbose_name_plural': 'сообщения от пользователей',
                'ordering': ('-created_at',),
            },
        ),
    ]
