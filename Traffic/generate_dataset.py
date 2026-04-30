#!/usr/bin/env python3
"""
generate_dataset.py — Генератор расширенного датасета для обучения AI-IPS.

Генерирует три сценария:
  0 = Нормальный офисный трафик (0–40 kbps, небольшие всплески)
  1 = DoS / ICMP Flood атака (700–1000 kbps)
  2 = Медленная атака / Slowloris (50–150 kbps) — перемаркируется в label=1

Итоговый файл: network_data.csv (500+ строк, 3 признака + label)
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)
OUTPUT = os.path.join(os.path.dirname(__file__), 'network_data.csv')

rows = []
base_ts = 1_780_000_000  # базовый timestamp

# ── СЦЕНАРИЙ 0: Норма (250 записей) ──────────────────────────────────────────
print("[*] Генерация: НОРМАЛЬНЫЙ трафик (250 точек)...")
for i in range(250):
    # user5 — обычный офисный пользователь, трафик 0–40 kbps
    u5  = max(0, np.random.normal(loc=5, scale=8))
    # Роутер несёт весь трафик офиса — чуть больше каждого пользователя
    rtr = max(0, np.random.normal(loc=30, scale=10))
    # Случайный всплеск (имитация скачивания файла)
    if np.random.random() < 0.05:
        u5  += np.random.uniform(20, 35)
        rtr += np.random.uniform(30, 60)
    rows.append({
        'timestamp':   base_ts + i,
        'user5_kbps':  round(u5, 4),
        'router_kbps': round(rtr, 4),
        'label':       0
    })

# ── СЦЕНАРИЙ 1: DoS / ICMP Flood (200 записей) ───────────────────────────────
print("[*] Генерация: DoS FLOOD атака (200 точек)...")
for i in range(200):
    # Пинг-флуд: user5 гонит 700–1000 kbps
    u5  = np.random.uniform(700, 1000)
    # Роутер при флуде тоже нагружен, но ответов нет (одностороннее)
    rtr = np.random.uniform(u5 * 0.7, u5 * 0.9)
    rows.append({
        'timestamp':   base_ts + 300 + i,
        'user5_kbps':  round(u5, 4),
        'router_kbps': round(rtr, 4),
        'label':       1
    })

# ── СЦЕНАРИЙ 2: Slow/Medium атака (100 записей) ───────────────────────────────
print("[*] Генерация: МЕДЛЕННАЯ атака (100 точек)...")
for i in range(100):
    # Атакующий не гонит флуд, но всё равно ≥ 50 kbps аномально для 1 юзера
    u5  = np.random.uniform(55, 160)
    # Роутер реагирует сильнее (много TCP-соединений)
    rtr = np.random.uniform(u5 * 1.0, u5 * 1.5)
    rows.append({
        'timestamp':   base_ts + 600 + i,
        'user5_kbps':  round(u5, 4),
        'router_kbps': round(rtr, 4),
        'label':       1
    })

# ── Переходные зоны (норма→атака и наоборот) — 50 записей ────────────────────
print("[*] Генерация: ПЕРЕХОДНЫЕ зоны (50 точек)...")
for i in range(25):
    # Нарастание атаки (0 → 700)
    progress = i / 25
    u5  = progress * np.random.uniform(500, 800)
    rtr = u5 * np.random.uniform(0.6, 0.8)
    label = 1 if u5 > 50 else 0
    rows.append({
        'timestamp':   base_ts + 800 + i,
        'user5_kbps':  round(u5, 4),
        'router_kbps': round(rtr, 4),
        'label':       label
    })

for i in range(25):
    # Затухание атаки (700 → 0)
    progress = (25 - i) / 25
    u5  = progress * np.random.uniform(400, 700)
    rtr = u5 * np.random.uniform(0.5, 0.7)
    label = 1 if u5 > 50 else 0
    rows.append({
        'timestamp':   base_ts + 830 + i,
        'user5_kbps':  round(u5, 4),
        'router_kbps': round(rtr, 4),
        'label':       label
    })

# ── Сохраняем ─────────────────────────────────────────────────────────────────
df = pd.DataFrame(rows)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # перемешиваем

df.to_csv(OUTPUT, index=False)

print(f"\n{'='*50}")
print(f"  Датасет сохранён: {OUTPUT}")
print(f"  Всего строк:      {len(df)}")
print(f"  Норма (0):        {(df.label==0).sum()}")
print(f"  Атака (1):        {(df.label==1).sum()}")
print(f"  Баланс классов:   {(df.label==0).sum()/(df.label==1).sum():.2f} : 1")
print(f"{'='*50}")
print(f"\n  Следующий шаг: python3 train_ai.py")
