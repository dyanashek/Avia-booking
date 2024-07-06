from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError

from .models import Delivery, Sender, Receiver, Address, Transfer

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        # Логика валидации для Delivery
        for transfer in self.instance.transfers.all():
            transfer.full_clean()  # Валидация каждого Transfer
        return cleaned_data


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = '__all__'
    
    def clean(self):
        print('i am here')
        try:
            pick_up = self.instance.pick_up
        except:
            pick_up = None

        if pick_up:
            try:
                address = self.instance.address
            except:
                address = None
            
            if not address:
                print('ошибка валидации')
                raise ValidationError('Адрес должен быть заполнен')
    
    def save(self, *args, **kwargs):
        print('and here')
        self.full_clean()  # Выполняет валидацию
        super().save(*args, **kwargs)