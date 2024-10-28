from django.http import JsonResponse


from currency.models import Contractor


def get_operation_types(request):
    contractor_id = request.GET.get('contractor_id')
    options = '<option value="">---------</option>'
    if contractor_id:
        contractor_type = Contractor.objects.get(id=contractor_id).agent_type
        
        if contractor_type == '1':
            options += f'<option value="1">получение usdt от контрагента</option>'
            options += f'<option value="2">передача шекелей контрагенту</option>'

        elif contractor_type == '2':
            options += f'<option value="3">получение usd от контрагента</option>'
            options += f'<option value="4">передача usdt контрагенту</option>'

    return JsonResponse({'options': options})
