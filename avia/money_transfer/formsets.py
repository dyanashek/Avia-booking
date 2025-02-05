from django.forms import BaseInlineFormSet, ValidationError

from money_transfer.models import Rate


class TransferInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        total_sum = 0
        if len(self.forms):
            for form in self.forms:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    usd_transfer = form.cleaned_data.get('usd_amount', 0)
                    if usd_transfer < 1:
                        raise ValidationError(f"Минимальная сумма к выдаче - 1$.")
                    total_sum += usd_transfer
            total_usd = round(self.instance.calculate_total_usd_amount(), 2)
            if not total_usd:
                raise ValidationError(f"Сумма к отправке не может равняться 0.")
            if not ( total_usd - 2 <= total_sum <= total_usd + 2):
                raise ValidationError(f"Сумма денег к выдаче ({total_sum}$) должна совпадать с точностью +/- 1$ с суммой переданных денежных средств ({total_usd}$).")
        else:
            raise ValidationError(f"Необходимо создать хотя бы один перевод к выдаче.")
