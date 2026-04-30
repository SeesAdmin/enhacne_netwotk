#!/bin/bash
# acl_check.sh — Полная диагностика ACL и маршрутизации
# Запускать: sudo bash /home/Diploma/Traffic/acl_check.sh

RED='\033[91m'; GREEN='\033[92m'; YELLOW='\033[93m'
CYAN='\033[96m'; BOLD='\033[1m'; RESET='\033[0m'
PASS=0; FAIL=0; WARN=0

log_pass() { echo -e "  ${GREEN}✅ PASS${RESET} $1"; ((PASS++)); }
log_fail() { echo -e "  ${RED}❌ FAIL${RESET} $1"; ((FAIL++)); }
log_warn() { echo -e "  ${YELLOW}⚠️  WARN${RESET} $1"; ((WARN++)); }
log_info() { echo -e "  ${CYAN}ℹ️ ${RESET} $1"; }
section()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${RESET}"; echo -e "${BOLD}${CYAN}  $1${RESET}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════${RESET}"; }

ping_test() {
  local FROM="$1" FROM_IP="$2" TO_IP="$3" EXPECT="$4" DESC="$5"
  local result
  result=$(docker exec "$FROM" ping -c 2 -W 2 "$TO_IP" 2>/dev/null | tail -1)
  if echo "$result" | grep -q "0 received\|100% packet loss\|unreachable"; then
    if [ "$EXPECT" = "BLOCK" ]; then
      log_pass "[$FROM→$TO_IP] ЗАБЛОКИРОВАНО (ожидалось) — $DESC"
    else
      log_fail "[$FROM→$TO_IP] НЕДОСТУПНО (ожидалось PASS) — $DESC"
    fi
  elif echo "$result" | grep -qE "[0-9]+ received"; then
    if [ "$EXPECT" = "PASS" ]; then
      log_pass "[$FROM→$TO_IP] ДОСТУПНО (ожидалось) — $DESC"
    else
      log_fail "[$FROM→$TO_IP] ДОСТУПНО (ожидалось BLOCK) — $DESC"
    fi
  else
    log_warn "[$FROM→$TO_IP] НЕИЗВЕСТНО ('$result') — $DESC"
  fi
}

curl_test() {
  local FROM="$1" TO_URL="$2" EXPECT="$3" DESC="$4"
  local code
  code=$(docker exec "$FROM" curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$TO_URL" 2>/dev/null)
  if [ "$code" = "200" ] || [ "$code" = "301" ] || [ "$code" = "302" ]; then
    if [ "$EXPECT" = "PASS" ]; then
      log_pass "[$FROM→$TO_URL] HTTP $code (ожидалось) — $DESC"
    else
      log_fail "[$FROM→$TO_URL] HTTP $code (ожидалось BLOCK) — $DESC"
    fi
  else
    if [ "$EXPECT" = "BLOCK" ]; then
      log_pass "[$FROM→$TO_URL] HTTP $code (заблокировано, ожидалось) — $DESC"
    else
      log_fail "[$FROM→$TO_URL] HTTP $code (ожидалось 200) — $DESC"
    fi
  fi
}

# ══════════════════════════════════════════════════
section "0. СОСТОЯНИЕ КОНТЕЙНЕРОВ"
# ══════════════════════════════════════════════════
for c in rtr-fw user5 user1 hr1 hr2 acc1 acc2 web1 srv1 boss1 admin1; do
  status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null)
  ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' "$c" 2>/dev/null | xargs)
  if [ "$status" = "running" ]; then
    log_pass "$c — running | IPs: $ip"
  else
    log_fail "$c — $status (не запущен!)"
  fi
done

# ══════════════════════════════════════════════════
section "1. IP FORWARDING НА RTR-FW"
# ══════════════════════════════════════════════════
fwd=$(docker exec rtr-fw cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)
if [ "$fwd" = "1" ]; then
  log_pass "ip_forward = 1 (роутер пересылает пакеты)"
else
  log_fail "ip_forward = $fwd (нужно включить!)"
  echo -e "  ${YELLOW}Fix: docker exec rtr-fw sysctl -w net.ipv4.ip_forward=1${RESET}"
fi

# ══════════════════════════════════════════════════
section "2. IPTABLES ПРАВИЛА НА RTR-FW"
# ══════════════════════════════════════════════════
policy=$(docker exec rtr-fw iptables -L FORWARD --line-numbers -n 2>/dev/null | head -3)
echo "$policy" | while read line; do log_info "$line"; done

rule_count=$(docker exec rtr-fw iptables -L FORWARD -n 2>/dev/null | grep -c "ACCEPT\|DROP\|REJECT" || echo 0)
if [ "$rule_count" -gt 3 ]; then
  log_pass "Найдено $rule_count правил FORWARD (ACL активны)"
else
  log_fail "Только $rule_count правил — ACL не применены! Запусти bootstrap/01_rtr_fw.sh"
fi

echo ""
echo "  Полная таблица FORWARD:"
docker exec rtr-fw iptables -L FORWARD -n --line-numbers 2>/dev/null | sed 's/^/    /'

# ══════════════════════════════════════════════════
section "3. МАРШРУТЫ В КОНТЕЙНЕРАХ"
# ══════════════════════════════════════════════════
for c in hr1 acc1 user5 boss1; do
  gw=$(docker exec "$c" ip route show default 2>/dev/null | awk '{print $3}')
  if [ -n "$gw" ]; then
    log_pass "$c — default via $gw"
  else
    log_fail "$c — НЕТ МАРШРУТА по умолчанию! (пакеты не пойдут через rtr-fw)"
    echo -e "  ${YELLOW}Fix: docker exec $c ip route add default via <GW>${RESET}"
  fi
done

# ══════════════════════════════════════════════════
section "4. PING: ШЛЮЗЫ (Базовая доступность)"
# ══════════════════════════════════════════════════
ping_test "hr1"    "10.10.20.10"  "10.10.20.254"  "PASS"  "hr1 → свой шлюз VLAN20"
ping_test "acc1"   "10.10.50.10"  "10.10.50.254"  "PASS"  "acc1 → свой шлюз VLAN50"
ping_test "user5"  "10.10.60.10"  "10.10.60.254"  "PASS"  "user5 → свой шлюз VLAN60"
ping_test "boss1"  "10.10.70.10"  "10.10.70.254"  "PASS"  "boss1 → свой шлюз VLAN70"

# ══════════════════════════════════════════════════
section "5. HTTP: ЛЕГИТИМНЫЙ ДОСТУП (Должен работать)"
# ══════════════════════════════════════════════════
curl_test "hr1"   "http://10.10.40.10"  "PASS"  "hr1 → srv1 HTTP (разрешено)"
curl_test "acc1"  "http://10.10.40.10"  "PASS"  "acc1 → srv1 HTTP (разрешено)"
curl_test "user1" "http://10.10.30.10"  "PASS"  "user1 → web1 DMZ HTTP (разрешено)"
curl_test "boss1" "http://10.10.40.10"  "PASS"  "boss1 → srv1 HTTP (разрешено)"

# ══════════════════════════════════════════════════
section "6. PING: МЕЖСЕГМЕНТНЫЙ (Политика)"
# ══════════════════════════════════════════════════
# Примечание: PING (ICMP) отдельно НЕ разрешён в ACL для большинства сегментов.
# По политике FORWARD DROP - ICMP будет заблокирован если нет явного ACCEPT ICMP.
echo -e "  ${YELLOW}ВАЖНО: ICMP/ping не прописан явно в ACL → будет DROP по умолчанию${RESET}"
echo -e "  ${YELLOW}Проверяем по факту (ожидаем BLOCK везде кроме admin/users с полным доступом)${RESET}"
echo ""

ping_test "hr1"   "10.10.20.10"  "10.10.40.10"  "BLOCK" "hr1 → srv1 PING (ICMP не в ACL)"
ping_test "acc1"  "10.10.50.10"  "10.10.40.10"  "BLOCK" "acc1 → srv1 PING (ICMP не в ACL)"
ping_test "hr1"   "10.10.20.10"  "10.10.50.10"  "BLOCK" "hr1 → Accounting (запрещено)"
ping_test "hr2"   "10.10.20.11"  "10.10.50.10"  "BLOCK" "hr2 → Accounting (запрещено)"
ping_test "user5" "10.10.60.10"  "10.10.40.10"  "BLOCK" "user5 → srv1 PING (ICMP не в ACL для users)"
ping_test "boss1" "10.10.70.10"  "10.10.20.10"  "BLOCK" "boss1 → HR (запрещено)"
ping_test "acc1"  "10.10.50.10"  "10.10.20.10"  "BLOCK" "acc1 → HR (запрещено)"

# ══════════════════════════════════════════════════
section "7. PING: ADMIN (Полный доступ)"
# ══════════════════════════════════════════════════
ping_test "admin1" "10.10.10.10" "10.10.40.10"  "PASS"  "admin1 → srv1 PING (admin полный доступ)"
ping_test "admin1" "10.10.10.10" "10.10.20.10"  "PASS"  "admin1 → hr1 PING (admin полный доступ)"
ping_test "admin1" "10.10.10.10" "10.10.50.10"  "PASS"  "admin1 → acc1 PING (admin полный доступ)"

# ══════════════════════════════════════════════════
section "8. ИТОГ"
# ══════════════════════════════════════════════════
TOTAL=$((PASS + FAIL + WARN))
echo ""
echo -e "  Всего тестов:   $TOTAL"
echo -e "  ${GREEN}✅ Прошло:${RESET}     $PASS"
echo -e "  ${RED}❌ Упало:${RESET}     $FAIL"
echo -e "  ${YELLOW}⚠️  Предупрежд:${RESET} $WARN"
echo ""
if [ "$FAIL" -gt 0 ]; then
  echo -e "  ${RED}${BOLD}ЕСТЬ ПРОБЛЕМЫ! Смотри секции выше.${RESET}"
  echo ""
  echo -e "  ${YELLOW}Типичные причины:${RESET}"
  echo -e "  1. Не запущен bootstrap: sudo bash Docker/bootstrap/01_rtr_fw.sh"
  echo -e "  2. Нет маршрутов в контейнерах: sudo bash Docker/bootstrap/05_fix_routes.sh"
  echo -e "  3. Не установлен nginx в web1/srv1: sudo bash Docker/bootstrap/02_servers.sh"
  echo -e "  4. ICMP не разрешён в ACL (это нормально — только HTTP-порты разрешены)"
else
  echo -e "  ${GREEN}${BOLD}Всё работает корректно!${RESET}"
fi
echo ""
