from django.core.management import BaseCommand
from django.db.models import Q

from core.models import TGText, Language
from config import SIM_MANAGER_USERNAME

class Command(BaseCommand):
    def handle(self, *args, **options):
        language = Language.objects.get(slug='rus')
        texts = [
            ['invoice_url', 'Ваша квитанция об оплате:'],
            ['sim_balance', 'Ваш баланс по симкарте (оплата наперед)'],
            ['collect_sim_money', 'Наш водитель свяжется с вами для уточнения деталей по оплате.'],
            ['address_correct_question', 'Это правильный адрес?'],
            ['pay_date', 'Дата платежа:'],
            ['sim_debt_future', 'Ваша задолженность по симкарте составит'],
            ['later_month_button', 'Оплачу через месяц'],
            ['later_week_button', 'Оплачу через неделю'],
            ['ready_pay_button', 'Готов оплатить'],
            ['payment_needed', 'Ее необходимо погасить в ближайшее время. Выберите из вариантов ниже:'],
            ['fare', 'Тариф:'],
            ['sim_debt', 'Ваша задолженность по симкарте'],
            ['new_sim_tax', '+50₪ единоразово за подключение'],
            ['short_month', 'мес.'],
            ['sim_application_accepted', f'Ваша заявка принята, свяжитесь с менеджером @{SIM_MANAGER_USERNAME} для назначения доставки и обсуждения деталей'],
            ['fare_price', 'Стоимость:'],
            ['fare_description', 'Описание тарифа:'],
            ['choose_fare', 'Выберите подходящий тариф:'],
            ['sim_button', 'Сим-карта'],
            ['choose_options', 'Выберите варианты:'],
            ['choose_route', 'Выберите направление:'],
            ['choose_departure_month', 'Выберите месяц отправления:'],
            ['choose_departure_day', 'Выберите день отправления:'],
            ['choose_arrival_day', 'Выберите день возвращения:'],
            ['phone_question', 'Пожалуйста, укажите свой номер телефона (введите или воспользуйтесь кнопкой ниже)'],
            ['address_question', 'Пожалуйста, укажите ваш адрес.'],
            ['passport_photo_question', 'Пожалуйста, отправьте фото вашего паспорта'],
            ['confirm_application', 'Подтвердите данные:'],
            ['contact_soon', 'Спасибо за заявку. Скоро с вами свяжемся.'],
            ['fio_receiver_question', 'Пожалуйста, введите ФИО получателя'],
            ['phone_receiver_question', 'Пожалуйста, введите телефон получателя'],
            ['flight_button', 'Билет'],
            ['parcel_button', 'Посылка'],
            ['confirm_button', 'Подтвердить'],
            ['back_button', 'Назад'],
            ['hand_write_button', 'Ввести вручную'],
            ['name_correct_question', 'Ваше имя'],
            ['familyname_correct_question', 'Ваша фамилия'],
            ['birth_correct_question', 'Ваша дата рождения'],
            ['start_correct_question', 'Ваш паспорт выдан'],
            ['end_correct_question', 'Срок действия вашего паспорта заканчивается'],
            ['passport_correct_question', 'Серия и номер вашего паспорта'],
            ['sex_correct_question', 'Ваш пол'],
            ['name_question', 'Пожалуйста, укажите ваше имя (латинскими буквами, согласно паспорту)'],
            ['familyname_question', 'Пожалуйста, укажите вашу фамилию (латинскими буквами, согласно паспорту)'],
            ['birth_question', 'Пожалуйста, введите вашу дату рождения в формате (дд.мм.гггг)'],
            ['start_question', 'Пожалуйста, введите дату выдачи паспорта в формате (дд.мм.гггг)'],
            ['end_question', 'Пожалуйста, введите дату окончания срока действия паспорта в формате (дд.мм.гггг)'],
            ['passport_question', 'Пожалуйста, введите серию и номер вашего паспорта (без пробельных символов)'],
            ['sex_question', 'Пожалуйста, выберите ваш пол:'],
            ['male_button', 'Мужской'],
            ['female_button', 'Женский'],
            ['name', 'Имя:'],
            ['familyname', 'Фамилия:'],
            ['passport', 'Номер паспорта:'],
            ['start', 'Дата выдачи паспорта:'],
            ['end', 'Окончание срока действия паспорта:'],
            ['birth', 'Дата рождения:'],
            ['route', 'Маршрут:'],
            ['type_flight', 'Перелет:'],
            ['departure', 'Дата отправления:'],
            ['arrival', 'Дата возвращения:'],
            ['address', 'Адрес:'],
            ['phone', 'Номер:'],
            ['phone_receiver', 'Номер получателя:'],
            ['fio_receiver', 'ФИО получателя:'],
            ['type_parcel', 'Тип отправления:'],
            ['welcome', 'Привет, тут вы сможете подать заявку на авиабилет и отправку посылок:'],
            ['contains_question', 'Пожалуйста, перечислите предметы в посылке'],
            ['error', 'Данные устарели, попробуйте снова'],
            ['oneway_button', 'В одну сторону'],
            ['roundtrip_button', 'Туда-обратно'],
            ['no_flights', 'На данный месяц рейсов не найдено'],
            ['choose_arrival_month', 'Выберите месяц возвращения:'],
            ['wrong_passport', 'Не удалось считать данные, попробуйте отправить другую фотографию паспорта (избегайте бликов и пересветов).'],
            ['request_phone_button', 'Предоставить номер'],
            ['request_location_button', 'Предоставить геопозицию'],
            ['not_valid', 'Данные не прошли валидацию, попробуйте снова.'],
            ['cancel_button', 'Отменить'],
            ['contains', 'Содержимое:'],
            ['receiver_phone', 'Номер телефона получателя:'],
            ['reuse', 'Использовать данные, введенные ранее:'],
            ['sex', 'Пол:'],
            ['faq', 'Вопрос-ответ'],
            ['later_date_button', 'Указать дату'],
            ['sim_payment_date', 'Укажите дату платежа в формате дд.мм.ггг (не должна превышать текущую более чем на месяц).'],
            ['sim_payment_date_error', 'Попробуйте еще раз.\nУкажите дату платежа в формате дд.мм.ггг (не должна превышать текущую более чем на месяц).']
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

