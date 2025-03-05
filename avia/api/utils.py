import hashlib
import hmac
import urllib.parse

from shop.models import BaseSettings


def validate_web_app_data(init_data: str):
    """Проверка подписи в запросе от Telegram mini app"""
    base_settings = BaseSettings.objects.first()
    if not base_settings:
        return False
    
    bot_token = base_settings.bot_token
    vals = {k: urllib.parse.unquote(v) for k, v in [s.split('=', 1) for s in init_data.split('&')]}
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(vals.items()) if k != 'hash')
    secret_key = hmac.new("WebAppData".encode(), bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)

    return h.hexdigest() == vals['hash']
