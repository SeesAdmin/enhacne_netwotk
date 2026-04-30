#!/bin/bash
set -e

echo "[*] Настройка серверного сегмента (srv1, web1)..."

#####################
# srv1 – файловый/приложений
#####################

docker exec srv1 bash -c '
set -e
echo "nameserver 8.8.8.8" > /etc/resolv.conf

apt update
DEBIAN_FRONTEND=noninteractive apt install -y samba openssh-server curl dnsutils

mkdir -p /srv/share
chmod 777 /srv/share

cp /etc/samba/smb.conf /etc/samba/smb.conf.bak 2>/dev/null || true

cat > /etc/samba/smb.conf << EOF
[global]
   workgroup = WORKGROUP
   server string = Diploma Samba Server
   security = user
   map to guest = Bad User

[share]
   path = /srv/share
   browsable = yes
   read only = no
   guest ok = yes
EOF

service smbd restart || systemctl restart smbd || true
service ssh restart || systemctl restart ssh || true

# Маршрут по умолчанию через rtr-fw
ip route del default || true
ip route add default via 10.10.40.254

echo "[srv1] setup done."
'

#####################
# web1 – nginx в DMZ (минимальный кастом)
#####################

docker exec web1 bash -c '
set -e

# Простая страничка, чтобы было видно, что это DMZ
cat > /usr/share/nginx/html/index.html << EOF
<html>
  <head><title>DMZ Web1</title></head>
  <body>
    <h1>DMZ Web Server (web1)</h1>
    <p>This host simulates an external-facing service in the DMZ.</p>
  </body>
</html>
EOF

echo "[web1] index.html updated."
'

echo "[*] Сервера настроены."

