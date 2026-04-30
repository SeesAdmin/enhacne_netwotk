#!/bin/bash
set -e

echo "[rtr-fw] init start..."

# Включаем форвардинг
sysctl -w net.ipv4.ip_forward=1 >/dev/null

# Сбрасываем старые правила
iptables -F
iptables -t nat -F

iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD DROP

# Разрешаем established/related
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# ADMIN INFRA (10.10.10.0/24) – полный доступ
iptables -A FORWARD -s 10.10.10.0/24 -j ACCEPT

# IT ADMINS (10.10.60.0/24) – полный доступ
iptables -A FORWARD -s 10.10.60.0/24 -j ACCEPT

# SERVERS -> интернет
iptables -A FORWARD -s 10.10.40.0/24 ! -d 10.10.0.0/16 -j ACCEPT

# HR -> srv1 (80,443,445) + интернет
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.40.10/32 -p tcp -m multiport --dports 80,443,445 -j ACCEPT
iptables -A FORWARD -s 10.10.20.0/24 ! -d 10.10.0.0/16 -j ACCEPT

# Accounting -> srv1 (80,443,445) + интернет
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.40.10/32 -p tcp -m multiport --dports 80,443,445 -j ACCEPT
iptables -A FORWARD -s 10.10.50.0/24 ! -d 10.10.0.0/16 -j ACCEPT

# Management -> srv1 (80,443) + интернет
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.40.10/32 -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A FORWARD -s 10.10.70.0/24 ! -d 10.10.0.0/16 -j ACCEPT

echo "[rtr-fw] FORWARD table:"
iptables -vnL FORWARD
echo "[rtr-fw] init done."
