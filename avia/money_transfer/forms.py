from import_export.forms import SelectableFieldsExportForm
from django import forms

from money_transfer.models import Delivery

class CustomExportForm(SelectableFieldsExportForm):
    authors = Delivery.objects.all().values_list('created_by__username', flat=True).distinct()
    choices = [(author, author) for author in authors]
    choices.insert(0, ('', 'Все'))
    date_from = forms.DateField(
        required=False,
        label='Дата от',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'})
    )
    date_to = forms.DateField(
        required=False,
        label='Дата до',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'date-input'})
    )
    author = forms.ChoiceField(
        choices=choices,
        required=False,
        label='Менеджер')
    