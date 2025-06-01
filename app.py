import webview
import requests
import os

API_BASE_URL = 'http://127.0.0.1:8000/accounts/api'




TOKEN_FILE = 'auth_token.txt'

def save_token(token):
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return f.read().strip()
    return ''




class Api:
    def __init__(self):
        self.captcha = ''
        self.username = ''
        self.token = load_token()

    def get_captcha(self):
        try:
            response = requests.get(f'{API_BASE_URL}/get-captcha/')
            if response.status_code == 200:
                self.captcha = response.json()['captcha']
                return self.captcha
            else:
                return f'Ошибка загрузки капчи: {response.status_code}'
        except Exception as e:
            return f'Ошибка загрузки капчи: {str(e)}'

    def login(self, username, password, captcha_answer):
        try:
            data = {
                'username': username,
                'password': password,
                'captcha': captcha_answer
            }
            response = requests.post(f'{API_BASE_URL}/login/', json=data)

            if response.headers.get('Content-Type') == 'application/json':
                res = response.json()
            else:
                return {'status': 'error', 'message': f'Ошибка от сервера: {response.status_code}'}

            if res['status'] == 'success':
                self.username = username
                token = res.get('token')
                if token:
                    self.token = token
                    save_token(token)
                return {'status': 'success'}
            elif res['status'] == '2fa_required':
                self.username = res.get('username')
                self._2fa_user_id = res.get('user_id')
                self._2fa_code = res.get('code')
                token = res.get('token')
                if token:
                    self.token = token
                    save_token(token)
                return {'status': '2fa_required', 'code': self._2fa_code}

            
            elif res['status'] == 'invalid_credentials':
                return {'status': 'error', 'message': 'Неверный логин или пароль.'}
            elif res['status'] == 'blocked':
                return {'status': 'error', 'message': 'Вы заблокированы. Попробуйте позже.'}
            elif res['status'] == 'too_many_requests':
                return {'status': 'error', 'message': 'Слишком много запросов. Подождите минуту.'}
            elif res['status'] == 'captcha_required':
                self.get_captcha()
                return {'status': 'error', 'message': 'Неправильная капча. Новая капча загружена.'}
            else:
                return {'status': 'error', 'message': 'Неизвестная ошибка.'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        

    def auto_login(self):
        if self.token:
            try:
                res = requests.post(f'{API_BASE_URL}/check-token/', json={'token': self.token})
                if res.status_code == 200 and res.json().get('status') == 'ok':
                    self.username = res.json()['username']
                    return True
            except:
                pass
        return False

    def get_success_page(self):
        return f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Добро пожаловать</title>
        </head>
        <body>
            <h1>Добро пожаловать, {self.username}!</h1>
            <p>Вы успешно вошли в систему.</p>
        </body>
        </html>
        """
    
    def verify_2fa(self, code):
        try:
            data = {'code': code, 'user_id': self._2fa_user_id}
            response = requests.post(f'{API_BASE_URL}/verify-2fa/', json=data)
            res = response.json()

            if res['status'] == 'success':
                new_token = res.get('token')
                if new_token:
                    self.token = new_token
                    save_token(new_token)
            return res
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

        
        
    def get_2fa_code(self):
        try:
            if not self.username:
                return "Нет логина"
            response = requests.post(f'{API_BASE_URL}/get-2fa-code/', json={'username': self.username})
            res = response.json()
            if res['status'] == 'ok':
                return res['code']
            elif res['status'] == 'waiting':
                return 'Ожидание кода...'
            else:
                return 'Ошибка получения кода'
        except Exception as e:
            return f'Ошибка: {str(e)}'


api = Api()

html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Авторизация</title>
    <style>
        body {{
            background-color: #000;
            font-family: 'Montserrat', sans-serif;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}

        .form-wrapper {{
            background-color: #111;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 12px 40px rgba(255, 255, 255, 0.08);
            width: 100%;
            max-width: 360px;
            display: flex;
            flex-direction: column;
            align-items: stretch;
        }}

        h2 {{
            font-size: 22px;
            text-align: center;
            margin-bottom: 24px;
        }}

        input {{
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid #333;
            background-color: #1a1a1a;
            color: #fff;
            font-size: 14px;
            margin-bottom: 16px;
        }}

        input::placeholder {{
            color: #888;
        }}

        input:focus {{
            outline: none;
            border-color: #555;
            background-color: #222;
        }}

        button {{
            padding: 14px;
            border: none;
            border-radius: 12px;
            background-color: #fff;
            color: #000;
            font-weight: 600;
            font-size: 15px;
            cursor: pointer;
            margin-top: 8px;
        }}

        button:hover {{
            background-color: #e0e0e0;
        }}

        .code-block {{
            font-size: 32px;
            font-weight: 700;
            background-color: #000;
            color: #00ff99;
            padding: 16px 24px;
            text-align: center;
            border-radius: 12px;
            margin: 24px 0;
            box-shadow: 0 0 12px rgba(0, 255, 150, 0.3);
            letter-spacing: 4px;
        }}


        #result {{
            font-size: 14px;
            text-align: center;
            color: red;
            margin-top: 8px;
        }}
    </style>
    <script>
        function loadCaptcha() {{
            window.pywebview.api.get_captcha().then(function (captcha) {{
                const captchaBox = document.getElementById('captcha_box');
                if (captcha.startsWith('Ошибка')) {{
                    captchaBox.innerText = captcha;
                }} else {{
                    document.getElementById('captcha_label').innerText = "Решите: " + captcha;
                    captchaBox.style.display = 'block';
                }}
            }});
        }}

        function login() {{
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const captcha = document.getElementById('captcha').value;

            window.pywebview.api.login(username, password, captcha).then(function (res) {{
                if (res.status === 'success') {{
                    window.pywebview.api.get_success_page().then(function (page) {{
                        document.documentElement.innerHTML = page;
                    }});
                }} else if (res.status === '2fa_required') {{
                    document.body.innerHTML = `
                        <div class="form-wrapper">
                            <h2>Ваш код 2FA</h2>
                            <div class="code-block">${{res.code}}</div>
                            <p>Введите этот код в браузере, чтобы подтвердить вход</p>
                        </div>
                    `;

                }} else {{
                    document.getElementById('result').innerText = res.message;
                    loadCaptcha();
                }}
            }});
        }}

        function submit2FA() {{
            const code = document.getElementById('code_2fa').value;
            window.pywebview.api.verify_2fa(code).then(function (res) {{
                if (res.status === 'success') {{
                    window.pywebview.api.get_success_page().then(function (page) {{
                        document.documentElement.innerHTML = page;
                    }});
                }} else {{
                    document.getElementById('result_2fa').innerText = res.message;
                }}
            }});
        }}

        window.onload = loadCaptcha;
    </script>
</head>
<body>
    <div class="form-wrapper">
        <h2>Авторизация</h2>
        <input type="text" id="username" placeholder="Логин">
        <input type="password" id="password" placeholder="Пароль">
        <div id="captcha_box" style="display: none;">
            <label id="captcha_label" for="captcha"></label>
            <input type="text" id="captcha" placeholder="Ответ">
        </div>
        <button onclick="login()">Войти</button>
        <p id="result"></p>
    </div>
</body>
</html>
"""


if __name__ == '__main__':
    if api.auto_login():
        html = api.get_success_page()
    window = webview.create_window('Авторизация', html=html, js_api=api, width=400, height=500)
    webview.start()
