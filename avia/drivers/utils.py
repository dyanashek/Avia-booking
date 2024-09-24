import json

from drivers.models import Driver


def construct_delivery_sim_message(sim, driver_id):
    driver = Driver.objects.filter(circuit_id=driver_id).first()
    if driver:
        message = f'''
                Вы подтвердили доставку симки: *{sim.sim_phone}*\
                \nПо адресу: *{sim.user.addresses}*\
                \nК оплате у клиента: *{sim.debt} ₪*\
                \n\
                \nВоспользуйтесь кнопками ниже для уточнения переданной клиентом суммы:\
                '''

        params = {
            'chat_id': driver.telegram_id,
            'text': message,
            'parse_mode': 'Markdown',
            'reply_markup': json.dumps({
                'inline_keyboard': [
                    [{'text': 'Указать сумму', 'callback_data': f'amount_{sim.pk}'}],
                    [{'text': 'Оплаты не было', 'callback_data': f'pass_{sim.pk}'}],
                ]
            })
        }

        return params


def construct_collect_sim_money_message(sim, driver_id):
    driver = Driver.objects.filter(circuit_id=driver_id).first()
    if driver:
        message = f'''
                Вы подтвердили сбор денег на сим-карту: *{sim.sim_phone}*\
                \nПо адресу: *{sim.user.addresses}*\
                \nК оплате у клиента: *{sim.debt} ₪*\
                \n\
                \nВоспользуйтесь кнопками ниже для уточнения переданной клиентом суммы:\
                '''

        params = {
            'chat_id': driver.telegram_id,
            'text': message,
            'parse_mode': 'Markdown',
            'reply_markup': json.dumps({
                'inline_keyboard': [
                    [{'text': 'Указать сумму', 'callback_data': f'amount_{sim.pk}'}],
                    [{'text': 'Оплаты не было', 'callback_data': f'pass_{sim.pk}'}],
                ]
            })
        }

        return params
        