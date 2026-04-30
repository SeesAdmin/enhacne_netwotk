import requests

# Пробуем более легкий эндпоинт, который берет данные последних секунд
URL = "http://localhost:19999/api/v1/data?chart=cgroup_user5.net_eth0&after=-1&points=1&format=json"

try:
    r = requests.get(URL, timeout=5)
    if r.status_code == 200:
        data = r.json()
        # Вытаскиваем значение Sent (обычно это второй индекс в списке 'data')
        # Структура ответа Netdata: {"data": [[timestamp, received, sent]]}
        val = data['data'][0][2] 
        print(f"Поток от User5: {val} kilobits/s")
    else:
        print(f"Ошибка сервера: {r.status_code}")
        print("Ответ:", r.text)
except Exception as e:
    print(f"Ошибка подключения: {e}")
