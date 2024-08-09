from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse

from parcels.models import Parcel
from parcels.utils import send_parcel_pickup_address
from core.models import ParcelVariation, Language


def get_parcel_variations(request):
    language = get_object_or_404(Language, slug='rus')

    variation_options = '<option value="">---------</option>'
    for variation in ParcelVariation.objects.filter(language=language).all():
        variation_options += f'<option value="{variation.id}">{variation.name}</option>'

    return JsonResponse({'variations': variation_options})


def parcel_send_circuit(request, pk):
    parcel = get_object_or_404(Parcel, id=pk)

    if parcel.circuit_api is False and parcel.valid:
        stop_id = send_parcel_pickup_address(parcel)
        if stop_id:
            parcel.circuit_id = stop_id
            parcel.circuit_api = True
            parcel.save()


    return redirect('/admin/parcels/parcel/')