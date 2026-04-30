import requests
import csv
import time
import os

# Используем точные эндпоинты
URL_U5 = "http://localhost:19999/api/v1/data?chart=cgroup_user5.net_eth0&after=-1&points=1&format=json"
URL_RTR = "http://localhost:19999/api/v1/data?chart=cgroup_rtr-fw.net_eth0&after=-1&points=1&format=json"
# АБСОЛЮТНЫЙ ПУТЬ
FILE_NAME = "/home/Diploma/Traffic/network_data.csv"

def get_metric(url):
    try:
        r = requests.get(url, timeout=1)
        if r.status_code == 200:
            return abs(float(r.json()['data'][0][2]))
        return 0.0
    except:
        return 0.0

print(f"[*] Сбор данных в: {FILE_NAME}")

with open(FILE_NAME, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "user5_kbps", "router_kbps", "label"])
    f.flush()

    try:
        while True:
            u5 = get_metric(URL_U5)
            rtr = get_metric(URL_RTR)
            label = 1 if u5 > 50 else 0
            
            writer.writerow([int(time.time()), u5, rtr, label])
            f.flush() # Мгновенная запись
            
            status = "ATTACK" if label == 1 else "Normal"
            print(f"[{status}] U5: {u5:.2f} | RTR: {rtr:.2f}", end='\r')
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Запись остановлена.")
