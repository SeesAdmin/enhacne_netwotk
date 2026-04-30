#!/bin/bash
# run_mvp.sh — Единый скрипт запуска MVP AI-IPS стенда
# Запускай из /home/Diploma/Traffic/
# Использование: bash run_mvp.sh [demo|shield|train|dataset|reset|check]

set -e
TRAFFIC_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$TRAFFIC_DIR/venv"
PYTHON="$VENV/bin/python3"

# Цвета
RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'; CYAN='\033[96m'
BOLD='\033[1m'; RESET='\033[0m'

banner() {
  echo -e "\n${BOLD}${CYAN}============================================${RESET}"
  echo -e "${BOLD}${CYAN}   AI-IPS MVP | Дипломный стенд${RESET}"
  echo -e "${BOLD}${CYAN}============================================${RESET}\n"
}

check_venv() {
  if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}[!] venv не найден: $VENV${RESET}"
    echo "    Создай venv: python3 -m venv venv && venv/bin/pip install scikit-learn pandas requests joblib"
    exit 1
  fi
}

check_docker() {
  if ! sudo docker ps --format '{{.Names}}' 2>/dev/null | grep -q rtr-fw; then
    echo -e "${RED}[!] Контейнер rtr-fw не запущен.${RESET}"
    echo "    Запусти: cd /home/Diploma/Docker && sudo docker compose up -d"
    exit 1
  fi
}

cmd_check() {
  echo -e "${CYAN}[*] Проверка состояния стенда...${RESET}\n"

  echo "── Docker контейнеры:"
  sudo docker ps --format "  {{.Names}}\t{{.Status}}" | grep -E "rtr-fw|user5|web1|ntopng"

  echo ""
  echo "── IP-адреса:"
  echo "  user5 (Атакующий): $(sudo docker exec user5 hostname -I 2>/dev/null || echo 'не запущен')"
  echo "  rtr-fw (Роутер):   $(sudo docker exec rtr-fw hostname -I 2>/dev/null || echo 'не запущен')"
  echo "  web1 (Цель):       $(sudo docker exec web1 hostname -I 2>/dev/null || echo 'не запущен')"

  echo ""
  echo "── Правила iptables (rtr-fw FORWARD):"
  sudo docker exec rtr-fw iptables -L FORWARD -n --line-numbers 2>/dev/null | head -20

  echo ""
  echo "── Netdata API:"
  curl -s "http://localhost:19999/api/v1/data?chart=cgroup_user5.net_eth0&after=-1&points=1&format=json" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  user5 трафик: {abs(d[\"data\"][0][2]):.2f} kbps')" 2>/dev/null \
    || echo "  [!] Netdata недоступна"
}

cmd_dataset() {
  echo -e "${CYAN}[*] Генерация датасета...${RESET}"
  check_venv
  cd "$TRAFFIC_DIR"
  "$PYTHON" generate_dataset.py
}

cmd_train() {
  echo -e "${CYAN}[*] Обучение модели...${RESET}"
  check_venv
  cd "$TRAFFIC_DIR"
  "$PYTHON" train_ai.py
}

cmd_demo() {
  echo -e "${CYAN}[*] Запуск авто-демо (атака + детекция + блокировка)...${RESET}"
  check_venv
  check_docker
  cd "$TRAFFIC_DIR"
  "$PYTHON" auto_demo.py
}

cmd_shield() {
  echo -e "${CYAN}[*] Запуск IPS в режиме мониторинга (без атаки)...${RESET}"
  check_venv
  check_docker
  cd "$TRAFFIC_DIR"
  "$PYTHON" ips_shield.py
}

cmd_reset() {
  echo -e "${YELLOW}[*] Сброс всех правил и процессов...${RESET}"
  sudo docker exec rtr-fw iptables -D FORWARD -s 10.10.60.10 -j DROP 2>/dev/null || true
  sudo docker exec user5 pkill -9 ping 2>/dev/null || true
  echo -e "${GREEN}[+] Сброшено.${RESET}"
}

# ── Меню ─────────────────────────────────────────────────────────────────────
banner

case "${1:-menu}" in
  check)   cmd_check   ;;
  dataset) cmd_dataset ;;
  train)   cmd_train   ;;
  demo)    cmd_demo    ;;
  shield)  cmd_shield  ;;
  reset)   cmd_reset   ;;
  *)
    echo -e "  Использование: ${BOLD}bash run_mvp.sh [команда]${RESET}\n"
    echo "  Команды:"
    echo -e "  ${GREEN}check${RESET}    — проверить состояние стенда (Docker + IPs + iptables)"
    echo -e "  ${GREEN}dataset${RESET}  — сгенерировать расширенный датасет (600 точек)"
    echo -e "  ${GREEN}train${RESET}    — обучить ML-модель на датасете"
    echo -e "  ${GREEN}demo${RESET}     — полное авто-демо (атака → детекция → блокировка)"
    echo -e "  ${GREEN}shield${RESET}   — только мониторинг (IPS без запуска атаки)"
    echo -e "  ${RED}reset${RESET}    — сбросить все правила iptables и остановить атаку"
    echo ""
    echo "  Порядок первого запуска:"
    echo -e "  ${BOLD}1.${RESET} bash run_mvp.sh dataset   # генерация данных"
    echo -e "  ${BOLD}2.${RESET} bash run_mvp.sh train     # обучение модели"
    echo -e "  ${BOLD}3.${RESET} bash run_mvp.sh check     # проверка стенда"
    echo -e "  ${BOLD}4.${RESET} bash run_mvp.sh demo      # демонстрация на защите"
    echo ""
    ;;
esac
