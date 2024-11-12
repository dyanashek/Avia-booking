import datetime

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from core.models import UsersSim
from sim.models import SimCard, Collect
from sim.utils import create_icount_client


def sim_resend_icount(request, pk):
    sim = get_object_or_404(SimCard, id=pk)
    
    if sim.icount_api is False and sim.icount_id is None:
        icount_client_id = create_icount_client(sim.name, sim.sim_phone)
        if icount_client_id:
            sim.icount_id = icount_client_id
            sim.icount_api = True
            sim.save()

    return redirect('/admin/sim/simcard/')


class SimDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'sim_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        sims = UsersSim.objects.filter(Q(ready_to_pay=True) |
                                (Q(circuit_id__isnull=False) & Q(collects__isnull=True))).order_by('-created_at').distinct()
        
        queryset = Collect.objects.order_by('-created_at').all()
        date_from = self.request.GET.get('date-from')
        if date_from:
            context['date_from'] = date_from
            date_from = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()
            queryset = queryset.filter(created_at__gte=date_from)
            sims = queryset.filter(pay_date__gte=date_from)
        date_to = self.request.GET.get('date-to')
        if date_to:
            context['date_to'] = date_to
            date_to = datetime.datetime.strptime(date_to, "%Y-%m-%d").date()
            queryset = queryset.filter(created_at__lte=date_to)
            sims = queryset.filter(pay_date__lte=date_to)

        context['sims'] = sims
        context['collects'] = queryset

        return context
