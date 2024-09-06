from django.shortcuts import get_object_or_404, redirect

from sim.models import SimCard
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
