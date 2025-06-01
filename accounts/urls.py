from django.urls import path
from .views import login_view, register_view, login_attempts_view, api_login_view, api_get_captcha, block_ip_view, login_attempts_json, two_factor_verify_view, api_verify_2fa, api_get_2fa_code, home
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('login-attempts/', login_attempts_view, name='login_attempts'),
    path('block-ip/<str:ip>/', block_ip_view, name='block_ip'),
    path('api/login-attempts/', login_attempts_json, name='login_attempts_json'),
    path('api/verify-2fa/', api_verify_2fa, name='api_verify_2fa'),
    path('api/get-2fa-code/', api_get_2fa_code, name='api_get_2fa_code'),

    path('api/get-captcha/', api_get_captcha, name='api_get_captcha'),
    path('api/login/', api_login_view, name='api_login_view'),
    path('2fa/', two_factor_verify_view, name='two_factor_verify')
]