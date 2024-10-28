import tempfile

import pandas

def create_excel_file(data, date_from, date_to):
    data_frame = pandas.DataFrame(data)
    data_frame.columns = ['Дата', 
                          'Контрагент', 
                          'Тип операции',
                          'Сумма',
                          'Валюта',
                          'Курс',
                          'Комиссия',
                        ]
                        
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
        date_from = date_from.strftime('%d.%m.%Y')
        date_to = date_to.strftime('%d.%m.%Y')
        data_frame.to_excel(temp_file.name, index=False, sheet_name=f'{date_from} - {date_to}')
        
        return temp_file.name