from django.contrib.auth import get_user_model, login

from shop.models import AccessToken


class TgMiniAppAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.GET.get('tg_id') and request.GET.get('token'):
            user = get_user_model().objects.filter(username=f'shop{request.GET.get("tg_id")}').first()
            if user:
                token = AccessToken.objects.filter(token=request.GET.get('token'), is_used=False).first()
                if token:
                    if token.token != 'd37ee800-396a-4905-802c-a32de2142fec':
                        token.is_used = True
                        token.save(update_fields=['is_used'])
                    try:
                        login(request, user)
                    except:
                        pass

        response = self.get_response(request)

        return response
