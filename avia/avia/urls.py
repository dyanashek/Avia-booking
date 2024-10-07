"""
URL configuration for avia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls.static import static

from money_transfer import views as money_transfer_views
from core import views as core_views
from tickets import views as tickets_view
from parcels import views as parcels_view
from sim import views as sim_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path('send_message/', core_views.send_message, name='send_message'),
    path('get_sender_addresses/', money_transfer_views.get_sender_addresses, name='sender_addresses'),
    path('get_sender_receivers/', money_transfer_views.get_sender_receivers, name='sender_receivers'),
    path('get_receiver_addresses/', money_transfer_views.get_receiver_addresses, name='receiver_addresses'),
    path('calculate_commission/', money_transfer_views.calculate_commission, name='calculate_commission'),
    path('stop_status/', money_transfer_views.stop_status, name='stop_status'),
    path('get_ticket_dates/', tickets_view.get_ticket_dates, name='ticket_dates'),
    path('get_parcel_variations/', parcels_view.get_parcel_variations, name='parcel_variations'),
    path('circuit/delivery/<int:pk>/', money_transfer_views.delivery_resend_circuit, name='delivery_circuit'),
    path('gspread/delivery/<int:pk>/', money_transfer_views.delivery_resend_gspread, name='delivery_gspread'),
    path('circuit/flight/<int:pk>/', core_views.flight_resend_circuit, name='flight_circuit'),
    path('circuit/parcel/<int:pk>/', core_views.parcel_resend_circuit, name='parcel_circuit'),
    path('circuit/sim/<int:pk>/', core_views.sim_resend_circuit, name='sim_circuit'),
    path('circuit/sim-collect/<int:pk>/', core_views.sim_resend_collect_circuit, name='sim_collect_circuit'),
    path('icount/sim/<int:pk>/', core_views.sim_resend_icount, name='sim_icount'),
    path('icount/sim-collect/<int:pk>/', core_views.sim_resend_collect_icount, name='sim_collect_icount'),
    path('circuit/ticket/<int:pk>/', tickets_view.ticket_send_circuit, name='circuit_admin_ticket'),
    path('circuit/admin-parcel/<int:pk>/', parcels_view.parcel_send_circuit, name='circuit_admin_parcel'),
    path('icount/admin-sim/<int:pk>/', sim_view.sim_resend_icount, name='sim_admin_icount'),
    path('money/report/', money_transfer_views.construct_report, name='money_transfer_report'),
    path('dialog/<str:dialog>/', core_views.DialogView.as_view(), name='dialog'),
    path('dialog/', core_views.DialogView.as_view(), name='dialogs'),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

