#!/bin/bash
TARGET="10.10.40.10" # Цель - наш главный сервер

echo "=== Выберите тип атаки ==="
echo "1) ICMP Flood (DDoS)"
echo "2) Port Scanning (Reconnaissance)"
read -p "Ваш выбор: " choice

case $choice in
    1)
        echo "[!] Запуск Flood-атаки с user5..."
        # -f шлет пакеты максимально быстро
        sudo docker exec -it user5 ping -f -s 1000 $TARGET
        ;;
    2)
        echo "[!] Запуск сканирования портов всей сети серверов..."
        # Если nmap нет, он попробует его поставить (нужен интернет в контейнере)
        sudo docker exec -it user5 bash -c "apt-get update && apt-get install -nmap -y > /dev/null && nmap -sS 10.10.40.0/24"
        ;;
    *)
        echo "Отмена."
        ;;
esac
