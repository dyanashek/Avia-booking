import json
import datetime

from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db.models import Q, OuterRef, Subquery
from django.db.models.functions import Greatest, Coalesce
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.urls import reverse

from core.models import Flight, Parcel, UsersSim, TGText, Notification, Language, TGUser, UserMessage
from core.utils import (send_pickup_address_sync, send_sim_delivery_address_sync, 
                        create_icount_client_sync, send_sim_money_collect_address_sync,
                        create_icount_invoice_sync)


@require_POST
def send_message(request):
    tg_id = request.POST.get('tg_id')
    text = request.POST.get('message')
    print(tg_id)
    print(text)
    if tg_id and text:
        print(2)
        user = get_object_or_404(TGUser, user_id=tg_id)
        Notification.objects.create(
                    user=user,
                    text=text,
                )

    return redirect(reverse('dialog', kwargs={'dialog': tg_id}))


def flight_resend_circuit(request, pk):
    flight = get_object_or_404(Flight, id=pk)

    if flight.circuit_api is False:
        stop_id = send_pickup_address_sync(flight, "flight")
        if stop_id:
            flight.circuit_id = stop_id
            flight.circuit_api = True
            flight.save()


    return redirect('/admin/core/flight/')


def parcel_resend_circuit(request, pk):
    parcel = get_object_or_404(Parcel, id=pk)

    if parcel.circuit_api is False:
        stop_id = send_pickup_address_sync(parcel, "parcel")
        if stop_id:
            parcel.circuit_id = stop_id
            parcel.circuit_api = True
            parcel.save()

    return redirect('/admin/core/parcel/')


def sim_resend_circuit(request, pk):
    sim = get_object_or_404(UsersSim, id=pk)

    if sim.circuit_api is False and sim.icount_api:
        stop_id = send_sim_delivery_address_sync(sim.sim_phone, sim.user, sim.fare)
        if stop_id:
            sim.circuit_id = stop_id
            sim.circuit_api = True
            sim.save()

    return redirect('/admin/core/userssim/')


def sim_resend_icount(request, pk):
    sim = get_object_or_404(UsersSim, id=pk)
    
    if sim.icount_api is False:
        icount_client_id = create_icount_client_sync(sim.user, sim.sim_phone)
        if icount_client_id:
            sim.icount_id = icount_client_id
            sim.icount_api = True
            sim.save()

    return redirect('/admin/core/userssim/')


def sim_resend_collect_circuit(request, pk):
    sim = get_object_or_404(UsersSim, id=pk)

    if sim.circuit_api_collect is False:
        stop_id = send_sim_money_collect_address_sync(sim.sim_phone, sim.user, sim.debt)
        if stop_id:
            sim.circuit_id_collect = stop_id
            sim.circuit_api_collect = True
            sim.save()

    return redirect('/admin/core/userssim/')


def sim_resend_collect_icount(request, pk):
    sim = get_object_or_404(UsersSim, id=pk)

    if sim.icount_api_collect is False and sim.icount_collect_amount > 0:
        doc_url = create_icount_invoice_sync(sim.icount_id, sim.icount_collect_amount, sim.is_old_sim)
        if doc_url:
            sim.icount_api_collect = True
            sim.icount_collect_amount = 0.0
            sim.save()

            sim_user = sim.user
            user_language = sim_user.language
            if not user_language:
                user_language = Language.objects.get(slug='rus')
            invoice_text = TGText.objects.get(slug='invoice_url', language=user_language)
            reply_text = f'{invoice_text.text} {doc_url}'
            Notification.objects.create(
                user=sim_user,
                text=reply_text,
            )

    return redirect('/admin/core/userssim/')


class DialogView(TemplateView):
    template_name = 'dialog.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        users_with_dialogs = TGUser.objects.filter(
            Q(stupid_messages__isnull=False) | Q(notifications__isnull=False)
        ).distinct()

        users_last_message = []

        for user in users_with_dialogs:
            users_last_message.append((user, user.newest_message,))

        users_last_message = [item[0] for item in sorted(users_last_message, key=lambda x: x[1], reverse=True)]
        
        context['dialogs'] = users_last_message

        curr_dialog = kwargs.get('dialog')
        if not curr_dialog and users_last_message:
            curr_dialog = users_last_message[0]
        elif curr_dialog and users_last_message:
            curr_dialog = TGUser.objects.filter(user_id=curr_dialog).first()

        context['curr_dialog'] = curr_dialog

        if curr_dialog:
            messages = []

            for outbox in UserMessage.objects.filter(user=curr_dialog).distinct():
                messages.append(
                    {
                        'outbox': True,
                        'message': outbox.message,
                        'date': outbox.created_at,
                    }
                )

            for outbox in Notification.objects.filter(user=curr_dialog).distinct():
                messages.append(
                    {
                        'outbox': False,
                        'message': outbox.text,
                        'date': outbox.notify_time,
                    }
                )
            
            messages = sorted(messages, key=lambda x: x.get('date'))
            context['messages'] = messages
        return context


