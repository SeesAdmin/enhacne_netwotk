import streamlit as st
import subprocess
import requests
import pandas as pd
import time
import os
from datetime import datetime

st.set_page_config(
    page_title="AI-IPS Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Стили ────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #1a1d26; border-right: 1px solid #2d3045; }
.metric-card {
    background: #1a1d26; border: 1px solid #2d3045; border-radius: 12px;
    padding: 16px; margin: 6px 0;
}
.pass-badge  { background:#1a3a2a; color:#4ade80; border:1px solid #4ade80; border-radius:6px; padding:2px 10px; font-size:13px; }
.fail-badge  { background:#3a1a1a; color:#f87171; border:1px solid #f87171; border-radius:6px; padding:2px 10px; font-size:13px; }
.warn-badge  { background:#3a2d1a; color:#fbbf24; border:1px solid #fbbf24; border-radius:6px; padding:2px 10px; font-size:13px; }
.block-badge { background:#2d1a3a; color:#a78bfa; border:1px solid #a78bfa; border-radius:6px; padding:2px 10px; font-size:13px; }
h1,h2,h3 { color: #e2e8f0 !important; }
.stTabs [data-baseweb="tab"] { color: #94a3b8; }
.stTabs [aria-selected="true"] { color: #6366f1 !important; border-bottom: 2px solid #6366f1; }
div[data-testid="stMetricValue"] { color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)

SUDO_PASS = "0905"

def run(cmd, timeout=8):
    try:
        r = subprocess.run(
            f"echo '{SUDO_PASS}' | sudo -S {cmd}",
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return ""

def docker(cmd, timeout=8):
    return run(f"docker {cmd}", timeout)

def get_containers():
    out = docker('ps --format "{{.Names}}|{{.Status}}|{{.Image}}"')
    rows = []
    for line in out.splitlines():
        if "|" in line:
            name, status, image = line.split("|", 2)
            rows.append({"name": name, "status": status, "image": image})
    return rows

def get_container_ips():
    names = ["rtr-fw","user5","user1","hr1","hr2","acc1","acc2",
             "web1","srv1","admin1","boss1"]
    result = {}
    for n in names:
        ip = docker(f'exec {n} hostname -I 2>/dev/null').split()
        result[n] = ip[0] if ip else "—"
    return result

def ping_test(frm, to):
    out = docker(f"exec {frm} ping -c 2 -W 2 {to}")
    if "2 received" in out or "1 received" in out:
        return True
    return False

def get_netdata(container="user5"):
    try:
        chart = f"cgroup_{container}.net_eth0"
        url = f"http://localhost:19999/api/v1/data?chart={chart}&after=-1&points=1&format=json"
        r = requests.get(url, timeout=2)
        val = abs(float(r.json()["data"][0][2]))
        return round(val, 2)
    except:
        return None

def get_iptables():
    return run("docker exec rtr-fw iptables -L FORWARD -n --line-numbers")

def read_log():
    log = "/home/Diploma/Traffic/ips_events.log"
    if os.path.exists(log):
        with open(log) as f:
            return f.read()
    return "Лог пуст"

# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🛡️ AI-IPS Control")
    st.markdown("---")
    st.markdown("### Быстрые действия")

    if st.button("🔄 Применить ACL (01_rtr_fw.sh)", use_container_width=True):
        with st.spinner("Применяю правила..."):
            out = run("bash /home/Diploma/Docker/bootstrap/01_rtr_fw.sh")
        st.success("ACL применены!")

    if st.button("🛣️ Исправить маршруты (.254)", use_container_width=True):
        with st.spinner("Настраиваю маршруты..."):
            out = run("bash /home/Diploma/Docker/bootstrap/05_fix_routes.sh")
        st.success("Маршруты настроены!")

    if st.button("🧹 Сбросить iptables блок", use_container_width=True):
        run("docker exec rtr-fw iptables -D FORWARD -s 10.10.60.10 -j DROP")
        run("docker exec user5 pkill -9 ping")
        st.success("Сброшено!")

    st.markdown("---")
    st.markdown("### 📡 Netdata")
    u5 = get_netdata("user5")
    if u5 is not None:
        color = "🔴" if u5 > 50 else "🟢"
        st.metric(f"{color} user5 трафик", f"{u5} kbps")
    else:
        st.warning("Netdata недоступна")

    st.markdown("---")
    st.caption("Diploma Project · AI-IPS")

# ═══════════════════════════════════════════════════════
# ШАПКА
# ═══════════════════════════════════════════════════════
st.markdown("# 🛡️ AI-IPS Network Dashboard")
st.markdown("*Corporate Network Security · VLAN + ACL · Streamlit UI*")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Статус сети",
    "🗺️ Топология",
    "🛡️ ACL Тесты",
    "🚀 Трафик",
    "📋 Логи"
])

# ═══════════════════════════════════════════════════════
# TAB 1 — Статус сети
# ═══════════════════════════════════════════════════════
with tab1:
    st.markdown("### Контейнеры Docker")

    if st.button("🔄 Обновить", key="refresh_containers"):
        st.rerun()

    containers = get_containers()
    if containers:
        col1, col2, col3 = st.columns(3)
        running = sum(1 for c in containers if "Up" in c["status"])
        col1.metric("Всего контейнеров", len(containers))
        col2.metric("🟢 Запущены", running)
        col3.metric("🔴 Остановлены", len(containers) - running)

        st.markdown("---")
        for c in sorted(containers, key=lambda x: x["name"]):
            is_up = "Up" in c["status"]
            icon = "🟢" if is_up else "🔴"
            st.markdown(
                f"{icon} **{c['name']}** — `{c['status']}` · *{c['image']}*"
            )
    else:
        st.error("Docker недоступен или контейнеры не запущены")

    st.markdown("---")
    st.markdown("### IP-адреса контейнеров")
    if st.button("Получить IP-адреса", key="get_ips"):
        with st.spinner("Запрашиваю..."):
            ips = get_container_ips()
        data = [{"Контейнер": k, "IP": v} for k, v in ips.items()]
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════
# TAB 2 — Топология
# ═══════════════════════════════════════════════════════
with tab2:
    st.markdown("### Топология сети")

    vlan_data = [
        {"VLAN": "VLAN10", "Подсеть": "10.10.10.0/24", "Шлюз": "10.10.10.254",
         "Узлы": "admin1 (.10), admin2 (.11)", "Роль": "Администраторы — полный доступ", "Цвет": "🔵"},
        {"VLAN": "VLAN20", "Подсеть": "10.10.20.0/24", "Шлюз": "10.10.20.254",
         "Узлы": "hr1 (.10), hr2 (.11)", "Роль": "HR — srv1 HTTP/SMB + интернет", "Цвет": "🟣"},
        {"VLAN": "VLAN30", "Подсеть": "10.10.30.0/24", "Шлюз": "10.10.30.254",
         "Узлы": "web1 (.10)", "Роль": "DMZ — публичный веб", "Цвет": "🟡"},
        {"VLAN": "VLAN40", "Подсеть": "10.10.40.0/24", "Шлюз": "10.10.40.254",
         "Узлы": "web1 (.10), srv1 (.10)", "Роль": "Серверный сегмент", "Цвет": "🟠"},
        {"VLAN": "VLAN50", "Подсеть": "10.10.50.0/24", "Шлюз": "10.10.50.254",
         "Узлы": "acc1 (.10), acc2 (.11)", "Роль": "Бухгалтерия — srv1 + интернет", "Цвет": "🟢"},
        {"VLAN": "VLAN60", "Подсеть": "10.10.60.0/24", "Шлюз": "10.10.60.254",
         "Узлы": "user5 (.10)⚠️, user1-4 (.11-.14)", "Роль": "Пользователи — DMZ + интернет", "Цвет": "🔴"},
        {"VLAN": "VLAN70", "Подсеть": "10.10.70.0/24", "Шлюз": "10.10.70.254",
         "Узлы": "boss1-3 (.10-.12)", "Роль": "Руководство — srv1 HTTP + интернет", "Цвет": "⚪"},
    ]

    df = pd.DataFrame(vlan_data)
    st.dataframe(
        df[["Цвет","VLAN","Подсеть","Шлюз","Узлы","Роль"]],
        use_container_width=True, hide_index=True
    )

    st.markdown("---")
    st.markdown("### ACL матрица доступа")
    st.markdown("*✅ Разрешено · ❌ Запрещено · 🌐 Только интернет*")

    acl_matrix = {
        "Откуда \\ Куда": ["Admin(10)", "HR(20)", "DMZ(30)", "Servers(40)", "Acc(50)", "Users(60)", "Boss(70)"],
        "Admin(10)":   ["—","✅","✅","✅","✅","✅","✅"],
        "HR(20)":      ["❌","—","❌","✅ HTTP/SMB","❌","❌","❌"],
        "DMZ(30)":     ["❌","❌","—","❌","❌","❌","❌"],
        "Servers(40)": ["❌","❌","❌","—","❌","❌","❌"],
        "Acc(50)":     ["❌","❌","❌","✅ HTTP/SMB","—","❌","❌"],
        "Users(60)":   ["❌","❌","✅ HTTP","❌","❌","—","❌"],
        "Boss(70)":    ["❌","❌","❌","✅ HTTP","❌","❌","—"],
    }
    st.dataframe(pd.DataFrame(acl_matrix).set_index("Откуда \\ Куда"),
                 use_container_width=True)

# ═══════════════════════════════════════════════════════
# TAB 3 — ACL Тесты
# ═══════════════════════════════════════════════════════
with tab3:
    st.markdown("### Тестирование ACL правил")
    st.info("Тесты выполняют ping между контейнерами и проверяют соответствие ACL политике")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Быстрые тесты")
        if st.button("▶️ Запустить все тесты", use_container_width=True):
            tests = [
                # (from, to,        expect, description)
                ("admin1", "10.10.20.10", True,  "Admin → HR (разрешено)"),
                ("admin1", "10.10.40.10", True,  "Admin → Servers (разрешено)"),
                ("admin1", "10.10.50.10", True,  "Admin → Accounting (разрешено)"),
                ("hr1",    "10.10.50.10", False, "HR → Accounting (BLOCK)"),
                ("hr1",    "10.10.10.10", False, "HR → Admin (BLOCK)"),
                ("acc1",   "10.10.20.10", False, "Acc → HR (BLOCK)"),
                ("acc1",   "10.10.10.10", False, "Acc → Admin (BLOCK)"),
                ("user5",  "10.10.10.10", False, "Users → Admin (BLOCK)"),
                ("boss1",  "10.10.20.10", False, "Boss → HR (BLOCK)"),
                ("boss1",  "10.10.50.10", False, "Boss → Acc (BLOCK)"),
            ]

            results = []
            progress = st.progress(0)
            status_box = st.empty()

            for i, (frm, to, expect, desc) in enumerate(tests):
                status_box.markdown(f"*Тестирую: {desc}...*")
                result = ping_test(frm, to)
                ok = (result == expect)
                results.append({
                    "Тест": desc,
                    "Ожидалось": "PASS" if expect else "BLOCK",
                    "Результат": "PASS" if result else "BLOCK",
                    "Статус": "✅" if ok else "❌"
                })
                progress.progress((i+1)/len(tests))

            status_box.empty()
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            passed = sum(1 for r in results if r["Статус"] == "✅")
            st.metric("Результат", f"{passed}/{len(results)} тестов прошло")

    with col2:
        st.markdown("#### Ручной тест")
        containers_list = ["admin1","hr1","hr2","acc1","acc2","user1","user5","boss1","web1","srv1"]
        frm = st.selectbox("Откуда", containers_list, key="manual_from")
        to_ip = st.text_input("Целевой IP", "10.10.40.10", key="manual_to")
        if st.button("🔍 Ping", use_container_width=True):
            with st.spinner(f"Пингую {frm} → {to_ip}..."):
                out = docker(f"exec {frm} ping -c 3 -W 2 {to_ip}")
            if out:
                st.code(out)
            else:
                st.error("Нет ответа / недоступно")

# ═══════════════════════════════════════════════════════
# TAB 4 — Трафик
# ═══════════════════════════════════════════════════════
with tab4:
    st.markdown("### Управление трафиком")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🟢 Нормальный трафик")
        if st.button("▶️ Запустить офисный трафик", use_container_width=True):
            run("bash /home/Diploma/Traffic/generate_normal.sh")
            st.success("Офисный трафик запущен в фоне!")

        if st.button("⏹️ Остановить трафик", use_container_width=True):
            for c in ["user1","user2","hr1","acc1","boss1"]:
                run(f"docker exec {c} pkill curl 2>/dev/null")
                run(f"docker exec {c} pkill ping 2>/dev/null")
            st.success("Фоновый трафик остановлен")

        st.markdown("---")
        st.markdown("#### 📊 Netdata — текущий трафик")
        if st.button("🔄 Обновить метрики"):
            pass
        for cont in ["user5", "rtr-fw"]:
            val = get_netdata(cont)
            if val is not None:
                color = "🔴" if val > 50 else "🟢"
                st.metric(f"{color} {cont}", f"{val:.2f} kbps")
            else:
                st.caption(f"{cont}: Netdata недоступна")

    with col2:
        st.markdown("#### 🔴 Атака (для демо IPS)")
        st.warning("⚠️ Только для демонстрации! Трафик будет заблокирован IPS.")

        attack_type = st.selectbox("Тип атаки", [
            "ICMP Flood (ping -f)",
            "Heavy ICMP (ping -f -s 1400)",
        ])

        if st.button("🚨 Запустить атаку", use_container_width=True):
            if "Heavy" in attack_type:
                cmd = "docker exec -d user5 ping -f -s 1400 10.10.40.10"
            else:
                cmd = "docker exec -d user5 ping -f 10.10.40.10"
            run(cmd)
            st.error("🚨 Атака запущена! user5 → 10.10.40.10")
            st.info("Запусти IPS: cd /home/Diploma/Traffic && venv/bin/python3 ips_shield.py")

        if st.button("⏹️ Остановить атаку", use_container_width=True):
            run("docker exec user5 pkill -9 ping")
            run("docker exec rtr-fw iptables -D FORWARD -s 10.10.60.10 -j DROP 2>/dev/null")
            st.success("Атака остановлена, блокировка снята")

        st.markdown("---")
        st.markdown("#### 🔧 iptables (rtr-fw)")
        if st.button("Показать FORWARD правила"):
            rules = get_iptables()
            if rules:
                st.code(rules, language="bash")
            else:
                st.warning("Нет данных")

# ═══════════════════════════════════════════════════════
# TAB 5 — Логи
# ═══════════════════════════════════════════════════════
with tab5:
    st.markdown("### Лог событий IPS")

    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("🔄 Обновить лог"):
            st.rerun()
        if st.button("🗑️ Очистить лог"):
            open("/home/Diploma/Traffic/ips_events.log", "w").close()
            st.success("Лог очищен")

    log_content = read_log()
    if log_content and log_content != "Лог пуст":
        lines = log_content.strip().split("\n")
        st.metric("Событий в логе", len(lines))
        st.code("\n".join(reversed(lines[-50:])), language="bash")
    else:
        st.info("Лог пуст. Запусти auto_demo.py или ips_shield.py чтобы появились события.")

    st.markdown("---")
    st.markdown("### Метрики модели")
    metrics_path = "/home/Diploma/Traffic/model_metrics.txt"
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            st.code(f.read(), language="text")
    else:
        st.warning("model_metrics.txt не найден. Запусти train_ai.py")
