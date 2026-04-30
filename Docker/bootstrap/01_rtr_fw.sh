#!/bin/bash
set -e

RTR="rtr-fw"

echo "[*] Настройка rtr-fw ..."

# Включаем IP forwarding внутри rtr-fw
docker exec "$RTR" sysctl -w net.ipv4.ip_forward=1 >/dev/null

# Чистим и настраиваем iptables внутри rtr-fw
docker exec "$RTR" bash -c '
set -e

# Сброс старых правил
iptables -F
iptables -t nat -F

# Базовые политики
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD DROP

# Разрешаем established-сессии
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

############################
#  СЕГМЕНТЫ
#  10.10.10.0/24  - admin infra
#  10.10.20.0/24  - HR
#  10.10.30.0/24  - DMZ
#  10.10.40.0/24  - Servers
#  10.10.50.0/24  - Accounting
#  10.10.60.0/24  - IT/Админы отдела
#  10.10.70.0/24  - Management
############################

##### ADMIN INFRA (10.10.10.0/24) #####
# Админский сегмент имеет полный доступ везде
iptables -A FORWARD -s 10.10.10.0/24 -j ACCEPT

##### USERS / Офисный сегмент (10.10.60.0/24) #####
# Пользователи могут ходить только в DMZ (80/443) и интернет
# ACL: НЕ разрешать в Admin, Servers напрямую, Accounting, Management
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.30.0/24 -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A FORWARD -s 10.10.60.0/24 ! -d 10.10.0.0/16 -j ACCEPT
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.10.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.20.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.40.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.50.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.70.0/24 -j REJECT --reject-with icmp-port-unreachable

##### SERVERS (10.10.40.0/24) #####
# Серверы могут ходить в интернет (обновления, внешние API)
iptables -A FORWARD -s 10.10.40.0/24 ! -d 10.10.0.0/16 -j ACCEPT

##### HR (10.10.20.0/24) #####
# HR -> внутренний сервер (srv1) по HTTP/HTTPS/SMB
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.40.10/32 -p tcp -m multiport --dports 80,443,445 -j ACCEPT
# HR -> интернет (кроме внутренних 10.10.0.0/16)
iptables -A FORWARD -s 10.10.20.0/24 ! -d 10.10.0.0/16 -j ACCEPT
# HR не лезет в админку, DMZ и другие отделы
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.10.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.30.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.50.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.60.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.20.0/24 -d 10.10.70.0/24 -j REJECT --reject-with icmp-port-unreachable

##### ACCOUNTING (10.10.50.0/24) #####
# Бухгалтерия -> сервер (srv1) HTTP/HTTPS/SMB (вся 1С, отчеты и т.д. можем повесить сюда)
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.40.10/32 -p tcp -m multiport --dports 80,443,445 -j ACCEPT
# Бухгалтерия -> интернет
iptables -A FORWARD -s 10.10.50.0/24 ! -d 10.10.0.0/16 -j ACCEPT
# Бухгалтерия не лезет в другие отделы и админку/DMZ
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.10.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.20.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.30.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.60.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.50.0/24 -d 10.10.70.0/24 -j REJECT --reject-with icmp-port-unreachable

##### MANAGEMENT (10.10.70.0/24) #####
# Руководство -> сервер (srv1) по HTTP/HTTPS (BI/отчеты)
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.40.10/32 -p tcp -m multiport --dports 80,443 -j ACCEPT
# Руководство -> интернет
iptables -A FORWARD -s 10.10.70.0/24 ! -d 10.10.0.0/16 -j ACCEPT
# Руководство не лезет в рабочие сегменты напрямую
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.10.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.20.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.30.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.50.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.70.0/24 -d 10.10.60.0/24 -j REJECT --reject-with icmp-port-unreachable

##### DMZ (10.10.30.0/24) #####
# Для простоты сейчас ничего не открываем изнутри в DMZ,
# потом можно добавить, например, Servers -> DMZ:443 и т.п.

echo "[rtr-fw] FORWARD rules configured:"
iptables -vnL FORWARD
'

echo "[*] rtr-fw готов."
