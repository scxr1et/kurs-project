import requests

for i in range(6):
    r = requests.post('http://127.0.0.1:8000/accounts/login/', data={
        'username': 'admin',
        'password': 'wrongpassword'
    })
    print(f'Попытка {i+1}: Статус-код {r.status_code}')
