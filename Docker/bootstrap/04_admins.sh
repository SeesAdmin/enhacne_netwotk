#!/bin/bash
set -e

echo "[*] Настройка admin1 и базового админского трафика..."

docker exec admin1 bash -c '
set -e
echo "nameserver 8.8.8.8" > /etc/resolv.conf
apt update
DEBIAN_FRONTEND=noninteractive apt install -y openssh-client curl dnsutils

mkdir -p /root/traffic

cat > /root/traffic/admin_ops.sh << EOF
#!/bin/bash

SERVER=10.10.40.10   # srv1

while true; do
  ssh -o StrictHostKeyChecking=no root@\${SERVER} \
    "date \\"+%F %T\\"; ls /srv/share 2>/dev/null | wc -l" \
    >/dev/null 2>&1

  if (( RANDOM % 3 == 0 )); then
    ssh -o StrictHostKeyChecking=no root@\${SERVER} \
      "tar cf /tmp/config_backup.tar /etc 2>/dev/null" \
      >/dev/null 2>&1
  fi

  sleep \$(( RANDOM % 20 + 10 ))
done
EOF

chmod +x /root/traffic/admin_ops.sh

# Маршрут по умолчанию через rtr-fw (admin-сегмент)
ip route del default 2>/dev/null || true
ip route add default via 10.10.10.254

echo "[admin1] готов. Можно запускать /root/traffic/admin_ops.sh"
'

echo "[*] Admin сегмент настроен."
