# Документация проекта: AI-IPS на базе VLAN и ACL

**Тема диплома:** Design and Modeling of a Corporate Network Using VLAN and ACL to Enhance Network Security  
**Расположение проекта:** `/home/Diploma/`

> [!IMPORTANT]
> После каждого `docker compose down/up` нужно заново запускать `01_rtr_fw.sh` и `05_fix_routes.sh` — настройки внутри контейнеров не сохраняются!

---

## 1. СТРУКТУРА ФАЙЛОВ

```
/home/Diploma/
├── Docker/
│   ├── docker-compose.yml          # Вся сеть: 7 VLAN, 18 контейнеров
│   ├── bootstrap/
│   │   ├── 01_rtr_fw.sh            # Роутер: ip_forward + ACL iptables
│   │   ├── 02_servers.sh           # nginx/samba на web1 и srv1
│   │   ├── 03_clients.sh           # curl в клиентских контейнерах
│   │   ├── 04_admins.sh            # Настройка admin-контейнеров
│   │   ├── 05_fix_routes.sh        # ⚠️ Маршруты через rtr-fw (.254)
│   │   └── init-rtr.sh             # Быстрая инициализация роутера
│   ├── vlan-dashboard/             # HTML дашборд (порт 8088)
│   └── ntopng-proxy/               # Прокси к Ntopng (порт 3001)
│
└── Traffic/
    ├── brain.pkl                   # Обученная ML-модель
    ├── network_data.csv            # Датасет 600 строк
    ├── model_metrics.txt           # Метрики для диплома
    ├── ips_events.log              # Лог событий IPS
    ├── generate_dataset.py         # Генератор датасета
    ├── collector.py                # Сбор реального трафика
    ├── train_ai.py                 # Обучение модели
    ├── auto_demo.py                # Авто-демо: атака→детекция→блокировка
    ├── ips_shield.py               # Постоянный мониторинг (без атаки)
    ├── generate_attack.sh          # Ручной запуск атаки
    ├── generate_normal.sh          # Фоновый офисный трафик
    ├── generate_office_life.sh     # Расширенная симуляция офиса
    ├── demo_acl.sh                 # Демо VLAN+ACL без ML
    ├── acl_check.sh                # Диагностика ACL
    ├── run_mvp.sh                  # Главный лаунчер
    ├── setup_mvp.sh                # Единоразовая настройка (sudo)
    └── venv/                       # Python (sklearn, pandas, joblib, requests)
```

---

## 2. СЕТЕВАЯ ТОПОЛОГИЯ

| VLAN | Подсеть | Шлюз | Контейнеры | Роль |
|------|---------|------|------------|------|
| VLAN10 | 10.10.10.0/24 | .254 | admin1(.10), admin2(.11) | Полный доступ везде |
| VLAN20 | 10.10.20.0/24 | .254 | hr1(.10), hr2(.11) | Только srv1 HTTP/SMB + интернет |
| VLAN30 | 10.10.30.0/24 | .254 | web1(.10) | DMZ — публичный веб |
| VLAN40 | 10.10.40.0/24 | .254 | web1(.10), srv1(.10) | Серверный сегмент |
| VLAN50 | 10.10.50.0/24 | .254 | acc1(.10), acc2(.11) | Только srv1 + интернет |
| VLAN60 | 10.10.60.0/24 | .254 | **user5(.10)★**, user1(.11)..user4(.14) | DMZ и интернет |
| VLAN70 | 10.10.70.0/24 | .254 | boss1(.10), boss2(.11), boss3(.12) | srv1 HTTP + интернет |

★ `user5 = 10.10.60.10` — **атакующий узел** для IPS-демо

> [!NOTE]
> `rtr-fw` подключён ко **всем 7 сетям** одновременно — он является шлюзом .254 в каждом VLAN и пропускает трафик через себя (ip_forward=1).

---

## 3. ACL ПРАВИЛА (01_rtr_fw.sh)

```bash
# Базовая политика
iptables -P FORWARD DROP       # всё запрещено по умолчанию
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
```

| Откуда | Куда | Порт | Действие |
|--------|------|------|----------|
| VLAN10 Admin | Везде | Любой | ACCEPT ✅ |
| VLAN60 Users | VLAN30 DMZ | TCP 80,443 | ACCEPT ✅ |
| VLAN60 Users | Интернет | Любой | ACCEPT ✅ |
| VLAN60 Users | Все внутренние | Любой | REJECT ❌ |
| VLAN20 HR | srv1 (10.10.40.10) | TCP 80,443,445 | ACCEPT ✅ |
| VLAN20 HR | VLAN40 | ICMP | ACCEPT ✅ |
| VLAN20 HR | Интернет | Любой | ACCEPT ✅ |
| VLAN20 HR | Остальные VLAN | Любой | REJECT ❌ |
| VLAN50 Acc | srv1 (10.10.40.10) | TCP 80,443,445 | ACCEPT ✅ |
| VLAN50 Acc | Интернет | Любой | ACCEPT ✅ |
| VLAN50 Acc | Остальные VLAN | Любой | REJECT ❌ |
| VLAN70 Boss | srv1 (10.10.40.10) | TCP 80,443 | ACCEPT ✅ |
| VLAN70 Boss | Интернет | Любой | ACCEPT ✅ |
| VLAN70 Boss | Остальные VLAN | Любой | REJECT ❌ |

---

## 4. КАК РАБОТАЕТ IPS — ЦЕПОЧКА

```
[1] user5 запускает ping flood → 750+ kbps

[2] Netdata API (localhost:19999) собирает метрики контейнера user5

[3] auto_demo.py каждую секунду:
    GET /api/v1/data?chart=cgroup_user5.net_eth0
    → получает u5_kbps

[4] ML-модель:
    df = DataFrame([[u5_kbps, rtr_kbps]])
    predict(df) → 1 (атака)

[5] Блокировка:
    docker exec rtr-fw iptables -I FORWARD -s 10.10.60.10 -j DROP
    (позиция 1 — срабатывает раньше всех правил)

[6] Запись в ips_events.log

[7] Через 60 сек тишины → авторазблокировка:
    iptables -D FORWARD -s 10.10.60.10 -j DROP
```

---

## 5. ML-МОДЕЛЬ

- **Алгоритм:** RandomForestClassifier (100 деревьев)
- **Библиотека:** scikit-learn (в `venv/`)
- **Признаки:** `user5_kbps` (вес 53%), `router_kbps` (вес 47%)
- **Датасет:** 600 строк — 255 норма / 345 атак
- **Accuracy:** 99.44% | **ROC-AUC:** 0.9999 | **False Negatives:** 0

### Как переобучить модель

```bash
cd /home/Diploma/Traffic
venv/bin/python3 generate_dataset.py   # новый датасет
venv/bin/python3 train_ai.py           # обучение → brain.pkl
```

---

## 6. ВСЕ КОМАНДЫ ЗАПУСКА

```bash
# ── Первый запуск (один раз) ──────────────────────────
cd /home/Diploma/Docker
sudo docker compose up -d                       # поднять все контейнеры
sudo bash bootstrap/01_rtr_fw.sh               # ACL на роутере
sudo bash bootstrap/02_servers.sh              # nginx/samba на серверах
sudo bash bootstrap/05_fix_routes.sh           # маршруты через rtr-fw ⚠️

# ── Обучение модели ───────────────────────────────────
cd /home/Diploma/Traffic
venv/bin/python3 generate_dataset.py
venv/bin/python3 train_ai.py

# ── Демо ─────────────────────────────────────────────
sudo bash run_mvp.sh demo        # полное авто-демо IPS
sudo bash demo_acl.sh            # тест VLAN+ACL без ML

# ── Утилиты ──────────────────────────────────────────
sudo bash run_mvp.sh check       # статус стенда
sudo bash run_mvp.sh reset       # сбросить iptables + убить ping
sudo bash acl_check.sh           # детальная диагностика ACL
```

---

## 7. ЧАСТЫЕ ПРОБЛЕМЫ

| Симптом | Причина | Решение |
|---------|---------|---------|
| Пинги не идут между VLAN | Маршруты через `.1` а не `.254` | `sudo bash bootstrap/05_fix_routes.sh` |
| BLOCK не работает (ping проходит) | ACL не применены | `sudo bash bootstrap/01_rtr_fw.sh` |
| `permission denied` на docker.sock | Нет sudo | `sudo bash script.sh` |
| HTTP 000 от hr1/acc1 | curl не установлен | `sudo bash bootstrap/03_clients.sh` |
| `brain.pkl not found` | Модель не обучена | `venv/bin/python3 train_ai.py` |
| IPS не блокирует | Маленький трафик | `ping -f -s 1400` вместо `-s 1000` |
| Netdata не отвечает | Контейнер упал | `sudo docker compose up -d ntopng` |

---

## 8. МОНИТОРИНГ

| Сервис | URL | Что показывает |
|--------|-----|----------------|
| Netdata | http://localhost:19999 | Трафик каждого контейнера |
| VLAN Dashboard | http://localhost:8088 | Дашборд сети |
| ntopng | http://localhost:3001 | Анализ трафика |

---

## 9. ЛОГ СОБЫТИЙ

Файл: `/home/Diploma/Traffic/ips_events.log`

```
[2026-03-27 16:30:44] [INFO]   === Запуск AI-IPS ===
[2026-03-27 16:30:46] [ALERT]  ML ОБНАРУЖИЛ АТАКУ | u5=748.3 kbps
[2026-03-27 16:30:46] [ALERT]  БЛОКИРОВКА | IP: 10.10.60.10 → DROP
[2026-03-27 16:31:46] [UNBLOCK] Разблокирован (60s тишины)
[2026-03-27 16:31:46] [INFO]   === IPS остановлена ===
```
