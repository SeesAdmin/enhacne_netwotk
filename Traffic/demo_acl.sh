#!/bin/bash
# Тест сегментации сети - проверяем что VLAN и ACL работают
# Запуск: sudo bash demo_acl.sh

echo "========================================"
echo " Тест сети: VLAN + ACL"
echo "========================================"

# Показываем текущие маршруты (не меняем)
echo ""
echo "--- Текущие маршруты (для справки) ---"
for c in hr1 acc1 user5 boss1 admin1; do
    gw=$(docker exec $c ip route show default 2>/dev/null | awk '{print $3}')
    echo "$c -> default via $gw"
done

# Показываем правила ACL на роутере
echo ""
echo "--- Правила iptables на rtr-fw (ACL) ---"
docker exec rtr-fw iptables -L FORWARD -n --line-numbers
echo ""

# ========================================
# ТЕСТ 1: внутри одного VLAN - должно работать
# ========================================
echo "========================================"
echo " ТЕСТ 1: Связь внутри одного VLAN"
echo " (пакеты не идут через rtr-fw, всегда OK)"
echo "========================================"

echo -n "hr1 -> hr2 (оба в VLAN20):    "
if docker exec hr1 ping -c 2 -W 2 10.10.20.11 &>/dev/null; then
    echo "OK - доступно"
else
    echo "FAIL"
fi

echo -n "acc1 -> acc2 (оба в VLAN50):  "
if docker exec acc1 ping -c 2 -W 2 10.10.50.11 &>/dev/null; then
    echo "OK - доступно"
else
    echo "FAIL"
fi

# ========================================
# ТЕСТ 2: admin имеет доступ везде
# ========================================
echo ""
echo "========================================"
echo " ТЕСТ 2: Admin (VLAN10) - полный доступ"
echo "========================================"

echo -n "admin1 -> hr1    (VLAN10->20): "
if docker exec admin1 ping -c 2 -W 2 10.10.20.10 &>/dev/null; then
    echo "OK - доступно (ожидалось)"
else
    echo "FAIL - должно быть доступно!"
fi

echo -n "admin1 -> acc1   (VLAN10->50): "
if docker exec admin1 ping -c 2 -W 2 10.10.50.10 &>/dev/null; then
    echo "OK - доступно (ожидалось)"
else
    echo "FAIL - должно быть доступно!"
fi

echo -n "admin1 -> srv1   (VLAN10->40): "
if docker exec admin1 ping -c 2 -W 2 10.10.40.10 &>/dev/null; then
    echo "OK - доступно (ожидалось)"
else
    echo "FAIL - должно быть доступно!"
fi

echo -n "admin1 -> web1   (VLAN10->30): "
if docker exec admin1 ping -c 2 -W 2 10.10.30.10 &>/dev/null; then
    echo "OK - доступно (ожидалось)"
else
    echo "FAIL - должно быть доступно!"
fi

# ========================================
# ТЕСТ 3: разрешённый HTTP-трафик
# ========================================
echo ""
echo "========================================"
echo " ТЕСТ 3: Разрешённый HTTP-доступ"
echo "========================================"

echo -n "user1 -> web1 HTTP   (VLAN60->30 port 80): "
code=$(docker exec user1 curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://10.10.30.10 2>/dev/null)
if [ "$code" = "200" ]; then
    echo "OK - HTTP $code (ожидалось)"
else
    echo "FAIL - получили HTTP $code"
fi

echo -n "hr1  -> srv1 HTTP    (VLAN20->40 port 80): "
code=$(docker exec hr1 curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://10.10.40.10 2>/dev/null)
if [ "$code" = "200" ]; then
    echo "OK - HTTP $code (ожидалось)"
else
    echo "FAIL - получили HTTP $code"
fi

echo -n "acc1 -> srv1 HTTP    (VLAN50->40 port 80): "
code=$(docker exec acc1 curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://10.10.40.10 2>/dev/null)
if [ "$code" = "200" ]; then
    echo "OK - HTTP $code (ожидалось)"
else
    echo "FAIL - получили HTTP $code"
fi

echo -n "boss1 -> srv1 HTTP   (VLAN70->40 port 80): "
code=$(docker exec boss1 curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://10.10.40.10 2>/dev/null)
if [ "$code" = "200" ]; then
    echo "OK - HTTP $code (ожидалось)"
else
    echo "FAIL - получили HTTP $code"
fi

# ========================================
# ТЕСТ 4: запрещённый трафик между отделами
# ========================================
echo ""
echo "========================================"
echo " ТЕСТ 4: Запрещённый трафик (BLOCK)"
echo "========================================"

echo -n "hr1  -> acc1  (VLAN20->50): "
if docker exec hr1 ping -c 2 -W 2 10.10.50.10 &>/dev/null; then
    echo "FAIL - пакет прошёл, но не должен был!"
else
    echo "OK - заблокировано (ожидалось)"
fi

echo -n "hr1  -> admin (VLAN20->10): "
if docker exec hr1 ping -c 2 -W 2 10.10.10.10 &>/dev/null; then
    echo "FAIL - пакет прошёл, но не должен был!"
else
    echo "OK - заблокировано (ожидалось)"
fi

echo -n "acc1 -> hr1   (VLAN50->20): "
if docker exec acc1 ping -c 2 -W 2 10.10.20.10 &>/dev/null; then
    echo "FAIL - пакет прошёл, но не должен был!"
else
    echo "OK - заблокировано (ожидалось)"
fi

echo -n "boss1 -> hr1  (VLAN70->20): "
if docker exec boss1 ping -c 2 -W 2 10.10.20.10 &>/dev/null; then
    echo "FAIL - пакет прошёл, но не должен был!"
else
    echo "OK - заблокировано (ожидалось)"
fi

echo -n "user5 -> srv1 (VLAN60->40): "
if docker exec user5 ping -c 2 -W 2 10.10.40.10 &>/dev/null; then
    echo "FAIL - пакет прошёл, но не должен был!"
else
    echo "OK - заблокировано (ожидалось)"
fi

echo -n "user5 -> admin (VLAN60->10): "
if docker exec user5 ping -c 2 -W 2 10.10.10.10 &>/dev/null; then
    echo "FAIL - пакет прошёл, но не должен был!"
else
    echo "OK - заблокировано (ожидалось)"
fi

echo -n "hr1  -> srv1 HTTP запрещён  (VLAN20->50): "
code=$(docker exec hr1 curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://10.10.50.10 2>/dev/null)
if [ "$code" = "200" ]; then
    echo "FAIL - HTTP $code, должно быть заблокировано!"
else
    echo "OK - HTTP $code - заблокировано (ожидалось)"
fi

echo -n "user5 -> srv1 HTTP запрещён (VLAN60->40): "
code=$(docker exec user5 curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://10.10.40.10 2>/dev/null)
if [ "$code" = "200" ]; then
    echo "FAIL - HTTP $code, должно быть заблокировано!"
else
    echo "OK - HTTP $code - заблокировано (ожидалось)"
fi

echo ""
echo "========================================"
echo " Тест завершён"
echo "========================================"
