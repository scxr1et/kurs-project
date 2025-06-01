from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.core.cache import cache
import random
from .models import BlockedIP, IPRangeCountry
from .models import LoginAttempt
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
import random
from django.http import JsonResponse
import json
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.utils.timezone import now
from django.template.loader import render_to_string
from .models import IPRangeCountry



MAX_FAILED_ATTEMPTS = 5
BLOCK_TIME = 10 * 60


RATE_LIMIT = 1000
RATE_LIMIT_TIMEOUT = 60


def log_login_attempt(username, ip_address, successful):
    LoginAttempt.objects.create(
        username=username,
        ip_address=ip_address,
        successful=successful
    )



User = get_user_model()
@login_required
def home(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        user.save()
        messages.success(request, 'Данные обновлены!')

    return render(request, 'home.html')

@csrf_exempt
def login_view(request):
    ip = get_client_ip(request)
    cache_key = f'failed_login_attempts_{ip}'
    blocked_key = f'blocked_ip_{ip}'
    captcha_key = f'captcha_required_{ip}'
    captcha_answer_key = f'captcha_answer_{ip}'
    captcha_text_key = f'captcha_text_{ip}'
    rate_limit_key = f'rate_limit_{ip}'

    is_blocked = cache.get(blocked_key)
    captcha_required = cache.get(captcha_key, False)
    captcha_text = cache.get(captcha_text_key)

    if request.method == 'POST' and not is_blocked:
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha_answer = request.POST.get('captcha')

        request_count = cache.get(rate_limit_key, 0) + 1
        cache.set(rate_limit_key, request_count, timeout=RATE_LIMIT_TIMEOUT)
        if request_count > RATE_LIMIT:
            return HttpResponse('Слишком много запросов. Попробуйте позже.', status=429)

        # капча проверка
        if captcha_required:
            expected = cache.get(captcha_answer_key)
            if not expected or captcha_answer != expected:
                # генерируем новую
                a, b = random.randint(1, 9), random.randint(1, 9)
                op = random.choice(['+', '-'])
                question = f"{a} {op} {b}"
                answer = str(eval(question))
                cache.set(captcha_text_key, question, timeout=300)
                cache.set(captcha_answer_key, answer, timeout=300)

                log_login_attempt(username, ip, False)
                messages.error(request, 'Неправильная капча. Попробуйте ещё раз.')
                return render(request, 'accounts/login.html', {
                    'captcha_required': True,
                    'captcha_text': question,
                    'is_blocked': False
                })

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            cache.delete(cache_key)
            cache.delete(captcha_key)
            log_login_attempt(username, ip, True)

            login_time = now().strftime('%Y-%m-%d %H:%M:%S')
            country = IPRangeCountry.get_country(ip) or 'Не определено'

            html_message = render_to_string('email/login_alert.html', {
                'username': user.username,
                'ip': ip,
                'country': country,
                'time': login_time,
                'logout_all_link': 'https://example.com/logout-all'
            })

            send_mail(
                subject='🔐 Вход в аккаунт',
                message='Письмо с HTML-версией',
                from_email=None,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            code = ''.join(random.choices('0123456789', k=6))
            signed_code = signing.dumps(code)
            cache.set(f'2fa_code_for_{user.username}', signed_code, timeout=300)

            send_mail(
                subject='Код подтверждения',
                message=f'Ваш код: {code}',
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False
            )



            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'status': '2fa_required', 'code': code, 'username': user.username})
            else:
                request.session['2fa_user'] = user.username
                return redirect('two_factor_verify')
        else:
            failed_attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, failed_attempts, timeout=BLOCK_TIME)

            if failed_attempts >= 1:
                cache.set(captcha_key, True, timeout=BLOCK_TIME)

                a, b = random.randint(1, 9), random.randint(1, 9)
                op = random.choice(['+', '-'])
                question = f"{a} {op} {b}"
                answer = str(eval(question))

                captcha_text = question
                cache.set(captcha_text_key, question, timeout=300)
                cache.set(captcha_answer_key, answer, timeout=300)


            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                cache.set(blocked_key, True, timeout=BLOCK_TIME)
                messages.error(request, 'Вы заблокированы на 10 минут из-за слишком большого количества попыток.')
            else:
                messages.error(request, f'Неверный логин или пароль. Попытка {failed_attempts}/{MAX_FAILED_ATTEMPTS}')

            log_login_attempt(username, ip, False)

    return render(request, 'accounts/login.html', {
        'captcha_required': True,
        'captcha_text': captcha_text,
        'is_blocked': is_blocked,
    })




@csrf_exempt
def register_view(request):
    ip = get_client_ip(request)
    cache_key = f'reg_failed_attempts_{ip}'
    blocked_key = f'reg_blocked_ip_{ip}'
    captcha_key = f'reg_captcha_required_{ip}'
    captcha_answer_key = f'reg_captcha_answer_{ip}'
    captcha_text_key = f'reg_captcha_text_{ip}'
    rate_limit_key = f'reg_rate_limit_{ip}'

    is_blocked = cache.get(blocked_key)
    captcha_required = cache.get(captcha_key, False)
    captcha_text = cache.get(captcha_text_key)

    if request.method == 'POST' and not is_blocked:
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha_answer = request.POST.get('captcha')

        # Rate limit
        request_count = cache.get(rate_limit_key, 0) + 1
        cache.set(rate_limit_key, request_count, timeout=RATE_LIMIT_TIMEOUT)
        if request_count > RATE_LIMIT:
            return HttpResponse('Слишком много запросов. Попробуйте позже.', status=429)

        # Капча
        if captcha_required:
            expected = cache.get(captcha_answer_key)
            if not expected or captcha_answer != expected:
                a, b = random.randint(1, 9), random.randint(1, 9)
                op = random.choice(['+', '-'])
                question = f"{a} {op} {b}"
                answer = str(eval(question))
                cache.set(captcha_text_key, question, timeout=300)
                cache.set(captcha_answer_key, answer, timeout=300)

                log_login_attempt(username, ip, False)
                messages.error(request, 'Неправильная капча.')
                return render(request, 'accounts/register.html', {
                    'captcha_required': True,
                    'captcha_text': question,
                    'is_blocked': False
                })

        # Проверка: существует ли уже такой пользователь
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь уже существует.')
            log_login_attempt(username, ip, False)
            return render(request, 'accounts/register.html', {
                'captcha_required': captcha_required,
                'captcha_text': captcha_text,
                'is_blocked': False
            })


        try:
            user = User.objects.create_user(username=username, password=password)
            user.save()

            cache.delete(cache_key)
            cache.delete(captcha_key)

            log_login_attempt(username, ip, True)
            login(request, user)

            return redirect('home')
        except Exception:
            failed_attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, failed_attempts, timeout=BLOCK_TIME)

            if failed_attempts >= 1:
                cache.set(captcha_key, True, timeout=BLOCK_TIME)

                a, b = random.randint(1, 9), random.randint(1, 9)
                op = random.choice(['+', '-'])
                question = f"{a} {op} {b}"
                answer = str(eval(question))
                cache.set(captcha_text_key, question, timeout=300)
                cache.set(captcha_answer_key, answer, timeout=300)

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                cache.set(blocked_key, True, timeout=BLOCK_TIME)
                messages.error(request, 'Вы заблокированы на 10 минут из-за слишком большого количества попыток.')
            else:
                messages.error(request, f'Ошибка регистрации. Попытка {failed_attempts}/{MAX_FAILED_ATTEMPTS}')

            log_login_attempt(username, ip, False)

    return render(request, 'accounts/register.html', {
        'captcha_required': captcha_required,
        'captcha_text': captcha_text,
        'is_blocked': is_blocked
    })





def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip






from django.contrib.auth.decorators import user_passes_test


@user_passes_test(lambda u: u.is_superuser)
def login_attempts_view(request):
    logs = LoginAttempt.objects.all().order_by('-timestamp')
    return render(request, 'accounts/login_attempts.html', {'logs': logs})







@staff_member_required
def login_attempts_json(request):
    attempts = LoginAttempt.objects.all().order_by('-timestamp')[:50]
    data = []

    for a in attempts:
        country = IPRangeCountry.get_country(str(a.ip_address)) or '—'
        data.append({
            'username': a.username or '-',
            'ip_address': str(a.ip_address),
            'successful': a.successful,
            'timestamp': a.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'country': country,
        })

    return JsonResponse({'logs': data})



@csrf_exempt
@staff_member_required
def block_ip_view(request, ip):
    BlockedIP.objects.get_or_create(ip_address=ip)
    return redirect('login_attempts')







#api






@csrf_exempt
def check_token(request):
    try:
        data = json.loads(request.body)
        token = data.get('token')
        username = cache.get(f'token_{token}')
        if username:
            return JsonResponse({'status': 'ok', 'username': username})
        return JsonResponse({'status': 'invalid'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})




def generate_2fa_code(user):
    code = ''.join(random.choices('0123456789', k=6))
    cache.set(f'2fa_{user.id}', code, timeout=30)
    return code


from django.contrib.auth import get_user_model

@csrf_exempt
def api_verify_2fa(request):
    try:
        data = json.loads(request.body)
        code = data.get('code')
        user_id = data.get('user_id')

        real_code = cache.get(f'2fa_{user_id}')

        if code == real_code:
            User = get_user_model()
            user = User.objects.get(id=user_id)
            new_token = get_random_string(32)
            cache.set(f'token_{new_token}', user.username, timeout=60 * 60 * 24)
            return JsonResponse({'status': 'success', 'token': new_token})

        else:
            return JsonResponse({'status': 'error', 'message': 'Неверный код'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})



@csrf_exempt
def api_get_2fa_code(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        code = cache.get(f'2fa_code_for_{username}')
        if code:
            return JsonResponse({'status': 'ok', 'code': code})
        else:
            return JsonResponse({'status': 'waiting'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def two_factor_verify_view(request):
    if request.method == 'POST':
        username = request.session.get('2fa_user')
        if not username:
            return redirect('login')

        code_entered = request.POST.get('code')
        code_real = cache.get(f'2fa_code_for_{username}')
        try:
            code_real = signing.loads(code_real)
        except signing.BadSignature:
            code_real = None

        if code_real == code_entered:
            request.session['2fa_passed'] = True
            return redirect('home')
        else:
            return render(request, 'accounts/2fa.html', {'error': 'Неверный код'})

    return render(request, 'accounts/2fa.html')



@csrf_exempt
def api_get_captcha(request):
    ip = get_client_ip(request)
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    op = random.choice(['+', '-'])

    if op == '+':
        answer = a + b
    else:
        answer = a - b

    question = f'{a} {op} {b}'

    cache_key_captcha_text = f'captcha_text_{ip}'
    cache_key_captcha_answer = f'captcha_answer_{ip}'

    cache.set(cache_key_captcha_text, question, timeout=300)
    cache.set(cache_key_captcha_answer, str(answer), timeout=300)

    return JsonResponse({'captcha': question})











@csrf_exempt
def api_login_view(request):
    ip = get_client_ip(request)
    cache_key = f'failed_login_attempts_{ip}'
    blocked_key = f'blocked_ip_{ip}'
    rate_limit_key = f'rate_limit_{ip}'
    captcha_text_key = f'captcha_text_{ip}'
    captcha_answer_key = f'captcha_answer_{ip}'

    is_blocked = cache.get(blocked_key)
    if is_blocked:
        return JsonResponse({'status': 'blocked'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            captcha_answer = data.get('captcha')
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Неверный формат запроса'}, status=400)

        request_count = cache.get(rate_limit_key, 0) + 1
        cache.set(rate_limit_key, request_count, timeout=RATE_LIMIT_TIMEOUT)

        if request_count > RATE_LIMIT:
            return JsonResponse({'status': 'too_many_requests'}, status=429)

        expected_answer = cache.get(captcha_answer_key)
        if expected_answer and str(captcha_answer) != str(expected_answer):
            log_login_attempt(username, ip, False)
            return JsonResponse({'status': 'captcha_required'}, status=400)

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            cache.delete(cache_key)
            cache.delete(captcha_answer_key)
            log_login_attempt(username, ip, True)

            from django.utils.crypto import get_random_string
            token = get_random_string(32)
            cache.set(f'token_{token}', user.username, timeout=60 * 60 * 24)

            code = ''.join(random.choices('0123456789', k=6))
            cache.set(f'2fa_code_for_{user.username}', code, timeout=300)

            return JsonResponse({
                'status': '2fa_required',
                'code': code,
                'username': user.username,
                'token': token,
                'user_id': user.id
            })

        else:
            failed_attempts = cache.get(cache_key, 0) + 1
            cache.set(cache_key, failed_attempts, timeout=BLOCK_TIME)

            if failed_attempts >= 1:
                cache.set(captcha_answer_key, expected_answer, timeout=BLOCK_TIME)

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                cache.set(blocked_key, True, timeout=BLOCK_TIME)
                return JsonResponse({'status': 'blocked'}, status=403)
            else:
                log_login_attempt(username, ip, False)
                return JsonResponse({'status': 'invalid_credentials'}, status=400)

    return JsonResponse({'status': 'method_not_allowed'}, status=405)
