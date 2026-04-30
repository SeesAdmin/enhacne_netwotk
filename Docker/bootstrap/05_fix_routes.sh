#!/bin/bash

# Массив: имя_контейнера:новый_шлюз
declare -A nodes=(
  ["admin1"]="10.10.10.254" ["admin2"]="10.10.10.254"
  ["hr1"]="10.10.20.254" ["hr2"]="10.10.20.254"
  ["web1"]="10.10.30.254"
  ["srv1"]="10.10.40.254"
  ["acc1"]="10.10.50.254" ["acc2"]="10.10.50.254"
  ["user1"]="10.10.60.254" ["user2"]="10.10.60.254" ["user3"]="10.10.60.254" ["user4"]="10.10.60.254" ["user5"]="10.10.60.254"
  ["boss1"]="10.10.70.254" ["boss2"]="10.10.70.254" ["boss3"]="10.10.70.254"
)

for node in "${!nodes[@]}"; do
    gateway="${nodes[$node]}"
    echo "[*] Исправление маршрута для $node -> $gateway"
    sudo docker exec "$node" ip route del default 2>/dev/null || true
    sudo docker exec "$node" ip route add default via "$gateway"
done

echo "[!] Все маршруты перенаправлены на rtr-fw (.254)"
