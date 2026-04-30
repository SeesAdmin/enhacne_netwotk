#!/usr/bin/env python3
"""
ips_shield.py — Продакшн-режим AI-IPS (без авто-атаки, только мониторинг).
Запускай отдельно: python3 ips_shield.py

Отличие от auto_demo.py:
  - НЕ запускает атаку сам
  - Работает непрерывно (не останавливается после первой блокировки)
  - Умеет разблокировать если атака прекратилась
  - Ведёт детальный лог
"""

import requests
import joblib
import pandas as pd
import os
import time
from datetime import datetime

# ─── Конфигурация ────────────────────────────────────────────────────────────
MODEL_PATH        = os.path.join(os.path.dirname(__file__), 'brain.pkl')
LOG_PATH          = os.path.join(os.path.dirname(__file__), 'ips_events.log')
URL_U5            = "http://localhost:19999/api/v1/data?chart=cgroup_user5.net_eth0&after=-1&points=1&format=json"
URL_RTR           = "http://localhost:19999/api/v1/data?chart=cgroup_rtr-fw.net_eth0&after=-1&points=1&format=json"
ATTACKER_IP       = "10.10.60.10"
POLL_INTERVAL     = 1     # секунд между опросами Netdata
AUTO_UNBLOCK_SECS = 60    # авто-разблокировка если тихо N секунд

# ─── Цвета ────────────────────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─── Загрузка модели ──────────────────────────────────────────────────────────
model = joblib.load(MODEL_PATH)
print(f"{GREEN}[OK]{RESET} Модель загружена. Мониторинг запущен.")
print(f"     Атакующий IP: {ATTACKER_IP} | Авто-разблокировка: {AUTO_UNBLOCK_SECS}s\n")

# ─── Функции ──────────────────────────────────────────────────────────────────
def log(level: str, msg: str):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    with open(LOG_PATH, 'a') as f:
        f.write(line + "\n")
    color = RED if level in ("ALERT", "BLOCK") else (GREEN if level == "UNBLOCK" else CYAN)
    print(f"\n{color}{line}{RESET}")

def get_val(url: str) -> float:
    try:
        r = requests.get(url, timeout=1)
        return abs(float(r.json()['data'][0][2]))
    except Exception:
        return 0.0

def run_iptables(action: str):
    """action: '-I' для блокировки, '-D' для разблокировки."""
    flag   = action  # -I или -D
    cmd    = f"sudo docker exec rtr-fw iptables {flag} FORWARD -s {ATTACKER_IP} -j DROP"
    result = os.popen(cmd).read()
    return result

def predict(u5: float, rtr: float) -> int:
    features = pd.DataFrame([[u5, rtr]], columns=['user5_kbps', 'router_kbps'])
    return int(model.predict(features)[0])

# ─── Главный цикл ─────────────────────────────────────────────────────────────
log("INFO", "=== IPS Shield запущен (продакшн-режим) ===")

is_blocked  = False
quiet_since = None
counter     = 0

print(f"  {'№':>4}  {'Время':<10} {'U5 kbps':>10} {'RTR kbps':>10} {'ML':>8}  {'Статус'}")
print(f"  {'-'*62}")

while True:
    u5  = get_val(URL_U5)
    rtr = get_val(URL_RTR)
    pred = predict(u5, rtr)
    counter += 1
    ts_now = datetime.now().strftime("%H:%M:%S")

    status = f"{RED}АТАКА {RESET}" if pred == 1 else f"{GREEN}НОРМА {RESET}"
    blocked_mark = f" {RED}[BLOCKED]{RESET}" if is_blocked else ""
    print(f"  {counter:>4}  {ts_now:<10} {u5:>10.2f} {rtr:>10.2f} {pred:>8}  {status}{blocked_mark}     ", end='\r')

    if pred == 1 and not is_blocked:
        log("BLOCK", f"АТАКА ОБНАРУЖЕНА | u5={u5:.1f} kbps | Блокирую {ATTACKER_IP}")
        run_iptables("-I")
        is_blocked  = True
        quiet_since = None

    elif is_blocked:
        if u5 < 10 and pred == 0:
            if quiet_since is None:
                quiet_since = time.time()
            elif time.time() - quiet_since >= AUTO_UNBLOCK_SECS:
                log("UNBLOCK", f"Тихий период {AUTO_UNBLOCK_SECS}s | Разблокирую {ATTACKER_IP}")
                run_iptables("-D")
                is_blocked  = False
                quiet_since = None
        else:
            quiet_since = None  # трафик снова поднялся — сбрасываем таймер

    time.sleep(POLL_INTERVAL)
