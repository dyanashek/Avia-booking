from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse

from core.models import Route
from tickets.models import Ticket
from tickets.utils import send_ticket_pickup_address

# Create your views here.
def get_ticket_dates(request):
    route_id = request.GET.get('route_id')
    if route_id:
        route = get_object_or_404(Route, id=route_id)
        reverse_route = route.opposite
        
        departure_date_options = '<option value="">---------</option>'
        for departure_dates in route.days.filter(day__gte=timezone.now().date()).all():
            departure_date_options += f'<option value="{departure_dates.id}">{departure_dates}</option>'

        arrival_date_options = '<option value="">---------</option>'
        for arrival_dates in reverse_route.days.filter(day__gte=timezone.now().date()).all():
            arrival_date_options += f'<option value="{arrival_dates.id}">{arrival_dates}</option>'

        return JsonResponse({'departure': departure_date_options, 'arrival': arrival_date_options})


def ticket_send_circuit(request, pk):
    ticket = get_object_or_404(Ticket, id=pk)

    if ticket.circuit_api is False and ticket.valid:
        stop_id = send_ticket_pickup_address(ticket)
        if stop_id:
            ticket.circuit_id = stop_id
            ticket.circuit_api = True
            ticket.save()


    return redirect('/admin/tickets/ticket/')