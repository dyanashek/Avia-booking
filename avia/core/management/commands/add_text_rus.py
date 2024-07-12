from django.core.management import BaseCommand
from django.db.models import Q

from core.models import TGText, Language
from config import SIM_MANAGER_USERNAME

class Command(BaseCommand):
    def handle(self, *args, **options):
        language = Language.objects.get(slug='rus')
        texts = [
            ['sim_button', 'Сим-карта'],
            ['choose_fare', 'Выберите подходящий тариф:'],
            ['back_button', 'Назад'],
            ['fare_description', 'Описание тарифа:'],
            ['fare_price', 'Стоимость:'],
            ['sim_application_accepted', f'Ваша заявка принята, свяжитесь с менеджером @{SIM_MANAGER_USERNAME} для назначения доставки и обсуждения деталей'],
            ['short_month', 'мес.'],
            ['new_sim_tax', '+50₪ единоразово за подключение'],
            ['sim_debt', 'Ваша задолженность по симкарте'],
            ['sim_debt_future', 'Ваша задолженность по симкарте составит'],
            ['fare', 'Тариф:'],
            ['payment_needed', 'Ее необходимо погасить в ближайшее время. Выберите из вариантов ниже:'],
            ['ready_pay_button', 'Готов оплатить'],
            ['later_week_button', 'Оплачу через неделю'],
            ['later_month_button', 'Оплачу через месяц'],
            ['pay_date', 'Дата платежа:'],
            ['address_correct_question', 'Это правильный адрес?'],
            ['collect_sim_money', 'Наш водитель свяжется с вами для уточнения деталей по оплате.']
        ]
        
        for item in texts:
            slug = item[0]
            text = item[1]
            if not TGText.objects.filter(Q(slug=slug) & Q(language=language)).exists():
                new_text = TGText(slug=slug, language=language, text=text)
                new_text.save()
            else:
                new_text = TGText.objects.filter(Q(slug=slug) & Q(language=language)).first()
                if new_text.text != text:
                    print(f'slug: {slug} уже существовал, с текстом: {new_text.text}. Заменен на: {text}')
                    new_text.text = text
                    new_text.save()
        
        print('done')