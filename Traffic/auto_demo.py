#!/usr/bin/env python3
"""
auto_demo.py — Автоматизированная демонстрация AI-IPS для диплома.
Запускает DoS-атаку, детектирует её через ML-модель и блокирует атакующего.

Архитектура:
  user5 (10.10.60.10) ──flood──► rtr-fw ──► web1/srv1 (10.10.40.10)
                                    │
                              [ML детекция]
                                    │
                              iptables DROP
"""

import subprocess
import time
import joblib
import requests
import pandas as pd
import warnings
import os
import sys
from datetime import datetime

warnings.filterwarnings("ignore")

# ─── Конфигурация ────────────────────────────────────────────────────────────
MODEL_PATH   = os.path.join(os.path.dirname(__file__), 'brain.pkl')
LOG_PATH     = os.path.join(os.path.dirname(__file__), 'ips_events.log')
URL_U5       = "http://localhost:19999/api/v1/data?chart=cgroup_user5.net_eth0&after=-1&points=1&format=json"
URL_RTR      = "http://localhost:19999/api/v1/data?chart=cgroup_rtr-fw.net_eth0&after=-1&points=1&format=json"
ATTACKER_IP  = "10.10.60.10"
TARGET_IP    = "10.10.40.10"
POLL_INTERVAL     = 1     # секунд между опросами
AUTO_UNBLOCK_SECS = 60    # авто-разблокировка если атака прекратилась

# ─── Цвета для терминала ──────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─── Загрузка модели ──────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*60}{RESET}")
print(f"{BOLD}   СИСТЕМА AI-IPS | Дипломный проект{RESET}")
print(f"{BOLD}{'='*60}{RESET}")

if not os.path.exists(MODEL_PATH):
    print(f"{RED}[ОШИБКА]{RESET} Файл brain.pkl не найден: {MODEL_PATH}")
    print(f"  Запустите сначала: python3 train_ai.py")
    sys.exit(1)

clf = joblib.load(MODEL_PATH)
print(f"{GREEN}[OK]{RESET} Модель Random Forest загружена: {MODEL_PATH}")
print(f"     Признаки модели: {clf.feature_names_in_.tolist() if hasattr(clf, 'feature_names_in_') else ['user5_kbps', 'router_kbps']}")

# ─── Функции ──────────────────────────────────────────────────────────────────
def log_event(level: str, message: str):
    """Пишет событие в лог-файл и в терминал."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}"
    with open(LOG_PATH, 'a') as f:
        f.write(line + "\n")
    color = RED if level == "ALERT" else (GREEN if level == "OK" else CYAN)
    print(f"{color}{line}{RESET}")

def get_traffic(url: str) -> float:
    """Получает значение трафика из Netdata API."""
    try:
        r = requests.get(url, timeout=1)
        return abs(float(r.json()['data'][0][2]))
    except Exception:
        return 0.0

def block_attacker():
    """Вставляет правило iptables DROP для атакующего IP."""
    cmd = f"sudo docker exec rtr-fw iptables -I FORWARD -s {ATTACKER_IP} -j DROP"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    if result.returncode == 0:
        log_event("ALERT", f"БЛОКИРОВКА АКТИВИРОВАНА | IP: {ATTACKER_IP} → DROP в iptables FORWARD")
    else:
        log_event("ERROR", f"Не удалось применить iptables: {result.stderr.decode().strip()}")

def unblock_attacker():
    """Удаляет правило блокировки из iptables."""
    cmd = f"sudo docker exec rtr-fw iptables -D FORWARD -s {ATTACKER_IP} -j DROP"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    if result.returncode == 0:
        log_event("OK", f"БЛОКИРОВКА СНЯТА | IP: {ATTACKER_IP} разблокирован (тихий период {AUTO_UNBLOCK_SECS}s)")
    else:
        pass  # правило уже удалено — нормально

def ml_predict(u5_kbps: float, rtr_kbps: float) -> int:
    """Запускает ML-модель и возвращает 0 (норма) или 1 (атака)."""
    features = pd.DataFrame([[u5_kbps, rtr_kbps]], columns=['user5_kbps', 'router_kbps'])
    return int(clf.predict(features)[0])

# ─── Главная логика ───────────────────────────────────────────────────────────
log_event("INFO", "=== Запуск AI-IPS системы ===")
print(f"\n{YELLOW}[1]{RESET} Запуск DoS-атаки (ping flood) с {ATTACKER_IP} на {TARGET_IP}...")
attack_proc = subprocess.Popen(
    f"sudo docker exec user5 ping -f -s 1000 {TARGET_IP}",
    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
log_event("INFO", f"Атака запущена: user5 ({ATTACKER_IP}) → ping flood → {TARGET_IP}")

print(f"{YELLOW}[2]{RESET} Мониторинг трафика. Ожидание аномалии...\n")
print(f"  {'Время':<22} {'U5 (kbps)':>12} {'RTR (kbps)':>12} {'Решение ML':>14}")
print(f"  {'-'*62}")

is_blocked      = False
blocked_at      = None   # время блокировки
quiet_since     = None   # время когда трафик стих после атаки

try:
    while True:
        u5  = get_traffic(URL_U5)
        rtr = get_traffic(URL_RTR)
        prediction = ml_predict(u5, rtr)

        ts_now = datetime.now().strftime("%H:%M:%S")
        decision = f"{RED}АТАКА{RESET}" if prediction == 1 else f"{GREEN}НОРМА{RESET}"

        print(f"  {ts_now:<22} {u5:>12.2f} {rtr:>12.2f}   {decision}     ", end='\r')

        if prediction == 1 and not is_blocked:
            # ── Атака обнаружена, блокируем ──────────────────────────────
            print()  # перенос строки чтобы не затирать вывод
            log_event("ALERT", f"ML ОБНАРУЖИЛ АТАКУ | u5={u5:.1f} kbps | rtr={rtr:.1f} kbps | предсказание=1")
            block_attacker()
            is_blocked  = True
            blocked_at  = time.time()
            quiet_since = None
            print(f"\n{BOLD}{RED}  ╔══════════════════════════════════════════╗{RESET}")
            print(f"{BOLD}{RED}  ║  АТАКА ЗАБЛОКИРОВАНА! Проверь iptables:  ║{RESET}")
            print(f"{BOLD}{RED}  ║  sudo docker exec rtr-fw iptables -L FORWARD -n -v  ║{RESET}")
            print(f"{BOLD}{RED}  ╚══════════════════════════════════════════╝{RESET}\n")

        elif is_blocked:
            # ── Следим — если трафик стих, через 60 с разблокируем ──────
            if u5 < 10:
                if quiet_since is None:
                    quiet_since = time.time()
                elif time.time() - quiet_since >= AUTO_UNBLOCK_SECS:
                    print()
                    unblock_attacker()
                    is_blocked  = False
                    blocked_at  = None
                    quiet_since = None
            else:
                quiet_since = None

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print(f"\n\n{YELLOW}[*]{RESET} Остановка по Ctrl+C. Очистка...")

finally:
    print(f"{YELLOW}[*]{RESET} Завершение. Сброс правил и остановка атаки...")
    unblock_attacker()
    attack_proc.terminate()
    subprocess.run("sudo docker exec user5 pkill -9 ping 2>/dev/null", shell=True)
    log_event("INFO", "=== IPS система остановлена, правила очищены ===")
    print(f"{GREEN}[+]{RESET} Стенд возвращён в исходное состояние.")
    print(f"{CYAN}[i]{RESET} Лог событий: {LOG_PATH}\n")
