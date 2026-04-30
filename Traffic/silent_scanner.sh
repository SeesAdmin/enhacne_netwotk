#!/bin/bash
echo "[!] Запуск скрытого сканирования из сети Юзеров..."
# Сканируем порты сервера srv1 медленно, чтобы имитировать разведку
docker exec -d user3 bash -c "apt-get update && apt-get install nmap -y > /dev/null; nmap -T2 10.10.40.10"
