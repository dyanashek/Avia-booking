from django.db import models


ERROR_SOURCE = (
    ('1', 'Основной бот'),
    ('2', 'Бот для водителей'),
    ('3', 'Бот для Самарканда'),
    ('4', 'Бот с отчетами'),
    ('5', 'Админка'),
)


ERROR_TYPE = (
    ('1', 'Ошибка редактирования/удаления сообщения'),
    ('2', 'Ошибка отправки сообщения'),
    ('3', 'Ошибка отправки точки в circuit'),
    ('4', 'Ошибка создания пользователя в iCount'),
    ('5', 'Ошибка создания квитанции в iCount'),
    ('6', 'Ошибка передачи данных в google table'),
    ('7', 'Ошибка обработки фото'),
    ('8', 'Ошибка определения адреса'),
    ('9', 'Ошибка обработки остановки по сбору за симкарту'),
    ('10', 'Ошибка внесение суммы собранной за симкарту'),
)


class AppError(models.Model):
    source = models.CharField(verbose_name='Источник ошибки', choices=ERROR_SOURCE, max_length=30)
    error_type = models.CharField(verbose_name='Тип ошибки', choices=ERROR_TYPE, max_length=30)
    main_user = models.CharField(verbose_name='Пользователь, у которого произошла ошибка', max_length=50, null=True, blank=True)
    connected_user = models.CharField(verbose_name='Связанный с ошибкой пользователь', max_length=50, null=True, blank=True)
    description = models.TextField(verbose_name='Описание ошибки', null=True, blank=True)
    created_at = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    resolved = models.BooleanField(verbose_name='Проблема решена?', null=True, blank=True, default=None)

    class Meta:
        verbose_name = 'ошибка'
        verbose_name_plural = 'ошибки'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.error_type} ({self.source})'
