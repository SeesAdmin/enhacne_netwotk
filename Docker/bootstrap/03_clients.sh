#!/bin/bash
set -e

echo "[*] Настройка клиентов отделов..."

# Функция настройки клиента: маршрут + базовые пакеты
setup_client() {
  local NAME="$1"
  local GW="$2"

  echo "  - [$NAME]"

  docker exec "$NAME" bash -c "
set -e
echo \"nameserver 8.8.8.8\" > /etc/resolv.conf
ip route del default 2>/dev/null || true
ip route add default via $GW

apt update
DEBIAN_FRONTEND=noninteractive apt install -y curl dnsutils smbclient cifs-utils

mkdir -p /root/traffic
echo \"[$NAME] ready.\"
" >/dev/null
}

######## HR: 10.10.20.0/24, GW 10.10.20.254 ########
for c in hr-pc1 hr-pc2 hr-pc3 hr-pc4; do
  setup_client "$c" "10.10.20.254"
done

######## ACCOUNTING: 10.10.50.0/24, GW 10.10.50.254 ########
for c in acc-pc1 acc-pc2 acc-pc3 acc-pc4; do
  setup_client "$c" "10.10.50.254"
done

######## IT ADMINS: 10.10.60.0/24, GW 10.10.60.254 ########
for c in it-pc1 it-pc2 it-pc3 it-pc4; do
  setup_client "$c" "10.10.60.254"
done

######## MANAGEMENT: 10.10.70.0/24, GW 10.10.70.254 ########
for c in mgmt-pc1 mgmt-pc2 mgmt-pc3 mgmt-pc4; do
  setup_client "$c" "10.10.70.254"
done

echo "[*] Клиенты отделов настроены."
