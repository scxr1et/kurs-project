from django.http import HttpResponseForbidden
from .models import BlockedIP, IPRangeCountry
from django.shortcuts import redirect

ALLOWED_COUNTRIES = {
    'RU', 'BY', 'KZ', 'AM', 'AZ', 'KG', 'MD', 'TJ', 'UZ',
}

class CountryBlockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = self.get_client_ip(request)


        if BlockedIP.objects.filter(ip_address=ip).exists():
            return HttpResponseForbidden("🛑 Ваш IP заблокирован")


        country_code = IPRangeCountry.get_country(ip)

        if not country_code or country_code.upper() not in ALLOWED_COUNTRIES:
            return HttpResponseForbidden("🌍 Доступ из вашей страны запрещён")

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        if ip == '127.0.0.1' or ip.startswith('192.168.'):
            ip = '46.174.104.122'

        return ip




class TwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.session.get('2fa_passed'):
            if request.path != '/2fa/':
                return redirect('two_factor_verify')
        return self.get_response(request)