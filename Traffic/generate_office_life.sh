#!/bin/bash
echo "[*] Запуск распределенной симуляции трафика..."

# --- VLAN 60 (Users) ---
# Легитимно: Веб-сервер
docker exec -d user1 bash -c "while true; do curl -s 10.10.30.10 > /dev/null; sleep 5; done"
# НАРУШЕНИЕ: Пытаемся залезть в Админку (Будет DROP)
docker exec -d user2 bash -c "while true; do timeout 1 tcpdump -i eth0; telnet 10.10.10.10 22; sleep 10; done"

# --- VLAN 20 (HR) ---
# Легитимно: Работа с сервером (80, 445)
docker exec -d hr1 bash -c "while true; do curl -s 10.10.40.10 > /dev/null; sleep 3; done"
# НАРУШЕНИЕ: HR лезет к Бухгалтерам (Будет DROP)
docker exec -d hr2 bash -c "while true; do ping -c 1 10.10.50.10; sleep 15; done"

# --- VLAN 50 (Accounting) ---
# Легитимно: База данных (445/TCP)
docker exec -d acc1 bash -c "while true; do nc -zv 10.10.40.10 445; sleep 7; done"
# НАРУШЕНИЕ: Пытаются пинговать интернет (если запрещено)
docker exec -d acc2 bash -c "while true; do ping -c 1 8.8.8.8; sleep 20; done"

# --- VLAN 70 (Management) ---
# Легитимно: Только Веб
docker exec -d boss1 bash -c "while true; do curl -s 10.10.40.10 > /dev/null; sleep 5; done"
# НАРУШЕНИЕ: Пытается зайти по SSH на сервер (Будет DROP)
docker exec -d boss2 bash -c "while true; do ssh 10.10.40.10; sleep 12; done"

echo "[+] Скрипты запущены. Сеть наполнена трафиком."
