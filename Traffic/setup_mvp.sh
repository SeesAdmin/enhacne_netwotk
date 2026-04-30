#!/bin/bash
# setup_mvp.sh — Единоразовый скрипт настройки прав и docker-compose
# Запускать один раз с sudo: sudo bash /home/Diploma/Traffic/setup_mvp.sh

set -e
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "\n${BOLD}=== MVP Setup Script (нужен sudo) ===${RESET}\n"

# ─── 1. Права на файлы ─────────────────────────────────────────────────────
echo -e "${YELLOW}[1/3] Исправление прав файлов...${RESET}"
chmod 666 /home/Diploma/Traffic/network_data.csv
chmod 644 /home/Diploma/Traffic/collector.py
chown seesoon:seesoon /home/Diploma/Traffic/network_data.csv
chown seesoon:seesoon /home/Diploma/Traffic/collector.py
echo -e "${GREEN}[OK] Права исправлены.${RESET}"

# ─── 2. Patch docker-compose.yml ───────────────────────────────────────────
echo -e "${YELLOW}[2/3] Патч docker-compose.yml (user5=.10, web1 в VLAN40)...${RESET}"

COMPOSE="/home/Diploma/Docker/docker-compose.yml"

python3 - <<'PYEOF'
import re

path = "/home/Diploma/Docker/docker-compose.yml"
content = open(path).read()
changed = False

# ── Паттерн для блока user1..user5 ──
# Найдём секцию офисных юзеров и переставим user5 первым со .10

old_block = """  # ===== Офисные юзеры (5 ПК) =====
  user1:
    image: ubuntu:22.04
    container_name: user1
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.10

  user2:
    image: ubuntu:22.04
    container_name: user2
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.11

  user3:
    image: ubuntu:22.04
    container_name: user3
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.12

  user4:
    image: ubuntu:22.04
    container_name: user4
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.13

  user5:
    image: ubuntu:22.04
    container_name: user5
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.14"""

new_block = """  # ===== Офисные юзеры (5 ПК) =====
  # ВАЖНО: user5 = 10.10.60.10 — АТАКУЮЩИЙ узел для IPS-демо
  user5:
    image: ubuntu:22.04
    container_name: user5
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.10

  user1:
    image: ubuntu:22.04
    container_name: user1
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.11

  user2:
    image: ubuntu:22.04
    container_name: user2
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.12

  user3:
    image: ubuntu:22.04
    container_name: user3
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.13

  user4:
    image: ubuntu:22.04
    container_name: user4
    command: ["sleep", "infinity"]
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan60_users:
        ipv4_address: 10.10.60.14"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("  [OK] user5 назначен IP 10.10.60.10 (атакующий)")
    changed = True
else:
    # Проверим, уже ли исправлено
    if "# ВАЖНО: user5 = 10.10.60.10" in content:
        print("  [SKIP] user5 уже исправлен")
    else:
        print("  [WARN] Блок user1..user5 не найден (возможно другой формат)")

# ── Добавляем web1 в vlan40 ──
old_web1 = """  # ===== DMZ (web1) =====
  web1:
    image: nginx:latest
    container_name: web1
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan30_dmz:
        ipv4_address: 10.10.30.10"""

new_web1 = """  # ===== DMZ (web1) — цель IPS-атаки (10.10.40.10) =====
  web1:
    image: nginx:latest
    container_name: web1
    tty: true
    cap_add:
      - NET_ADMIN
    networks:
      vlan30_dmz:
        ipv4_address: 10.10.30.10
      vlan40_servers:
        ipv4_address: 10.10.40.10"""

if old_web1 in content:
    content = content.replace(old_web1, new_web1)
    print("  [OK] web1 добавлен в vlan40 (10.10.40.10 — цель атаки)")
    changed = True
elif "vlan40_servers:" in content and "web1" in content[:content.find("vlan40_servers:")]:
    print("  [SKIP] web1 уже в vlan40")
else:
    print("  [WARN] Блок web1 не найден")

if changed:
    open(path, 'w').write(content)
    print("  [OK] docker-compose.yml обновлён")
PYEOF

echo -e "${GREEN}[OK] docker-compose.yml обработан.${RESET}"

# ─── 3. Исправить ACL для VLAN60 (Users) в 01_rtr_fw.sh ───────────────────
echo -e "${YELLOW}[3/3] Исправление ACL для VLAN60 (ограничиваем user5)...${RESET}"

RTR_SCRIPT="/home/Diploma/Docker/bootstrap/01_rtr_fw.sh"

# Заменяем "IT-сегмент имеет полный доступ" на ограниченный ACL
python3 - <<'PYEOF'
path = "/home/Diploma/Docker/bootstrap/01_rtr_fw.sh"
content = open(path).read()

old_vlan60 = """##### IT / Админы отдела (10.10.60.0/24) #####
# IT-сегмент тоже имеет полный доступ (внутренняя админка)
iptables -A FORWARD -s 10.10.60.0/24 -j ACCEPT"""

new_vlan60 = """##### USERS / Офисный сегмент (10.10.60.0/24) #####
# Пользователи могут ходить только в DMZ (80/443) и интернет
# ACL: НЕ разрешать в Admin, Servers напрямую, Accounting, Management
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.30.0/24 -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A FORWARD -s 10.10.60.0/24 ! -d 10.10.0.0/16 -j ACCEPT
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.10.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.20.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.40.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.50.0/24 -j REJECT --reject-with icmp-port-unreachable
iptables -A FORWARD -s 10.10.60.0/24 -d 10.10.70.0/24 -j REJECT --reject-with icmp-port-unreachable"""

if old_vlan60 in content:
    content = content.replace(old_vlan60, new_vlan60)
    open(path, 'w').write(content)
    print("  [OK] ACL для VLAN60 исправлен (users ограничены)")
elif "USERS / Офисный сегмент" in content:
    print("  [SKIP] ACL VLAN60 уже исправлен")
else:
    print("  [WARN] Блок VLAN60 не найден — исправь вручную")
PYEOF

echo -e "${GREEN}[OK] bootstrap/01_rtr_fw.sh обновлён.${RESET}"

echo -e "\n${BOLD}${GREEN}=== Настройка завершена! ===${RESET}"
echo ""
echo "  Следующие шаги:"
echo "  1. cd /home/Diploma/Traffic"
echo "  2. venv/bin/python3 generate_dataset.py   # генерация датасета"
echo "  3. venv/bin/python3 train_ai.py            # обучение модели"
echo "  4. bash run_mvp.sh check                   # проверка стенда"
echo "  5. bash run_mvp.sh demo                    # демо для диплома"
echo ""
