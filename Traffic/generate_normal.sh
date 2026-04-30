#!/bin/bash
echo "[*] Запуск имитации нормального трафика..."

# Юзеры (VLAN 60) запрашивают сайт в DMZ (VLAN 30) раз в 2 секунды
docker exec -d user1 bash -c "while true; do curl -s http://10.10.30.10 > /dev/null; sleep 2; done"
docker exec -d user2 bash -c "while true; do curl -s http://10.10.30.10 > /dev/null; sleep 3; done"

# Бухгалтерия (VLAN 50) пингует сервер базы данных (VLAN 40)
docker exec -d acc1 bash -c "while true; do ping -i 5 10.10.40.10 > /dev/null; done"

# HR (VLAN 20) запрашивает сервер
docker exec -d hr1 bash -c "while true; do curl -s http://10.10.40.10 > /dev/null; sleep 4; done"

echo "[+] Офисный шум запущен в фоновом режиме."
