# Generated by Django 4.2 on 2025-03-29 12:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('errors', '0003_alter_apperror_error_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apperror',
            name='error_type',
            field=models.CharField(choices=[('1', 'Ошибка редактирования/удаления сообщения'), ('2', 'Ошибка отправки сообщения'), ('3', 'Ошибка отправки точки в circuit'), ('4', 'Ошибка создания пользователя в iCount'), ('5', 'Ошибка создания квитанции в iCount'), ('6', 'Ошибка передачи данных в google table'), ('7', 'Ошибка обработки фото'), ('8', 'Ошибка определения адреса'), ('9', 'Ошибка обработки остановки по сбору за симкарту'), ('10', 'Ошибка внесение суммы собранной за симкарту'), ('11', 'Ошибка создания пользователя в iCount (магазин)')], max_length=30, verbose_name='Тип ошибки'),
        ),
    ]
