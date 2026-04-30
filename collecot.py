import requests
import csv
import time

# Список графиков, которые мы мониторим
CHARTS = {
    "user5": "cgroup_user5.net_eth0",
    "user1": "cgroup_user1.net_eth0",
    "router": "cgroup_rtr-fw.net_eth0"
}

def get_val(chart_id):
    url = f"http://localhost:19999/api/v1/data?chart={chart_id}&after=-1&points=1&format=json"
    try:
        r = requests.get(url, timeout=2)
        # Берем абсолютное значение (abs), чтобы избавиться от минусов
        return abs(float(r.json()['data'][0][2])) 
    except:
        return 0.0

print("[*] Сборщик данных запущен.")
print("[!] Инструкция: Сначала запиши 1-2 минуты НОРМЫ, потом включи АТАКУ.")

filename = "network_dataset.csv"
with open(filename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'user5_kbps', 'user1_kbps', 'router_kbps', 'is_attack'])
    
    try:
        while True:
            u5 = get_val(CHARTS["user5"])
            u1 = get_val(CHARTS["user1"])
            rtr = get_val(CHARTS["router"])
            
            # Авто-метка: если user5 гонит больше 50 кбит/с, считаем это атакой
            label = 1 if u5 > 50 else 0
            
            writer.writerow([int(time.time()), u5, u1, rtr, label])
            
            status = "ATTACK!" if label == 1 else "Normal"
            print(f"[{status}] U5: {u5:.2f} | U1: {u1:.2f} | RTR: {rtr:.2f}")
            
            time.sleep(1) # Запись каждую секунду
    except KeyboardInterrupt:
        print(f"\n[*] Готово! Данные сохранены в {filename}")
