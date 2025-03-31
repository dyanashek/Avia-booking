from django.contrib.auth.models import AnonymousUser

from shop.models import BuyerProfile
from shop.utils import format_amount


def global_context(request):
    if not isinstance(request.user, AnonymousUser):
        if buyer := BuyerProfile.objects.filter(user=request.user).first():
            curr_buyer_balance = format_amount(buyer.balance)
    return locals()
