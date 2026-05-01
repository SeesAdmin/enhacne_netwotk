import streamlit as st
import subprocess
import requests
import pandas as pd
import os

st.set_page_config(page_title="Network Dashboard", page_icon="", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #1a1d26; border-right: 1px solid #2d3045; }
h1,h2,h3,h4 { color: #e2e8f0 !important; }
.stTabs [data-baseweb="tab"] { color: #94a3b8; font-size: 14px; }
.stTabs [aria-selected="true"] { color: #6366f1 !important; border-bottom: 2px solid #6366f1; }
.cnt-card {
    background: #1a1d26; border: 1px solid #2d3045; border-radius: 10px;
    padding: 10px 14px; margin: 4px 0; color: #e2e8f0; font-size: 13px;
}
.result-row {
    padding: 6px 12px; border-radius: 6px; margin: 3px 0; font-size: 13px;
    font-family: monospace;
}
.r-pass  { background:#0d2818; border-left: 3px solid #4ade80; color: #86efac; }
.r-block { background:#1e1030; border-left: 3px solid #a78bfa; color: #c4b5fd; }
.r-fail  { background:#2d0f0f; border-left: 3px solid #f87171; color: #fca5a5; }
.flow-box {
    background: #1a1d26; border: 1px solid #2d3045; border-radius: 10px;
    padding: 14px 18px; margin: 6px 0; font-family: monospace; font-size: 13px; color: #e2e8f0;
}
.flow-arrow { color: #6366f1; font-weight: bold; }
.flow-ok { color: #4ade80; }
.flow-block { color: #f87171; }
div[data-testid="stMetricValue"] { color: #e2e8f0; font-size: 2rem !important; }
</style>
""", unsafe_allow_html=True)

SUDO = "0905"

def run(cmd, timeout=10):
    try:
        r = subprocess.run(f"echo '{SUDO}' | sudo -S {cmd}",
                           shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ""

def dexec(container, cmd, timeout=8):
    return run(f"docker exec {container} {cmd}", timeout)

def ping_test(frm, to, timeout=5):
    out = run(f"docker exec {frm} ping -c 2 -W 2 {to}", timeout)
    return ("2 received" in out) or ("1 received" in out)

def http_test(frm, url, timeout=6):
    code = run(f'docker exec {frm} curl -s -o /dev/null -w "%{{http_code}}" --connect-timeout 3 {url}', timeout)
    return code in ("200","301","302"), code

def get_containers():
    out = run('docker ps --format "{{.Names}}|{{.Status}}|{{.Image}}"')
    rows = []
    for line in out.splitlines():
        if "|" in line:
            n, s, img = line.split("|", 2)
            rows.append({"name": n.strip(), "status": s.strip(), "image": img.strip()})
    return sorted(rows, key=lambda x: x["name"])

def get_ips():
    names = ["admin1","admin2","hr1","hr2","web1","srv1","acc1","acc2",
             "user1","user2","user3","user4","user5","boss1","boss2","boss3","rtr-fw"]
    result = {}
    for n in names:
        out = run(f"docker exec {n} hostname -I 2>/dev/null")
        result[n] = out.split()[0] if out.strip() else "—"
    return result

# ─── SIDEBAR ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Network Dashboard")
    st.markdown("VLAN + ACL Diploma Project")
    st.markdown("---")
    st.markdown("**Quick Actions**")
    if st.button("Apply ACL rules", use_container_width=True):
        with st.spinner("Applying..."):
            run("bash /home/Diploma/Docker/bootstrap/01_rtr_fw.sh")
        st.success("ACL applied")
    if st.button("Fix routes (.254)", use_container_width=True):
        with st.spinner("Fixing..."):
            run("bash /home/Diploma/Docker/bootstrap/05_fix_routes.sh")
        st.success("Routes fixed")
    if st.button("Reset iptables block", use_container_width=True):
        run("docker exec rtr-fw iptables -D FORWARD -s 10.10.60.10 -j DROP 2>/dev/null")
        run("docker exec user5 pkill -9 ping 2>/dev/null")
        st.success("Reset done")
    st.markdown("---")
    st.caption("branch: acl-vlan-demo")

# ─── TITLE ──────────────────────────────────────────────────────
st.markdown("# Network Dashboard")
st.markdown("Corporate Network · VLAN Segmentation · ACL Security")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "Network Status",
    "Topology",
    "Traffic Tests",
    "Logs"
])

# ═══════════════════════════════════════════════════════
# TAB 1 — Network Status
# ═══════════════════════════════════════════════════════
with tab1:
    st.markdown("### Container Status")
    col_r, col_btn = st.columns([6, 1])
    with col_btn:
        if st.button("Refresh", key="ref1"):
            st.rerun()

    containers = get_containers()
    total = len(containers)
    running = sum(1 for c in containers if "Up" in c["status"])
    stopped = total - running

    c1, c2, c3 = st.columns(3)
    c1.metric("Total containers", total)

    run_color = "#4ade80" if running > 0 else "#e2e8f0"
    stop_color = "#f87171" if stopped > 0 else "#e2e8f0"

    c2.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-radius:8px;padding:12px 16px">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px">Running</div>
        <div style="font-size:2rem;font-weight:700;color:{run_color}">{running}</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-radius:8px;padding:12px 16px">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px">Stopped</div>
        <div style="font-size:2rem;font-weight:700;color:{stop_color}">{stopped}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    # Two-column container list
    left_containers = containers[:len(containers)//2 + len(containers)%2]
    right_containers = containers[len(containers)//2 + len(containers)%2:]
    col_l, col_r2 = st.columns(2)
    with col_l:
        for c in left_containers:
            up = "Up" in c["status"]
            dot = '<span style="color:#4ade80">●</span>' if up else '<span style="color:#f87171">●</span>'
            st.markdown(f'<div class="cnt-card">{dot} <b>{c["name"]}</b> — {c["status"]}</div>',
                        unsafe_allow_html=True)
    with col_r2:
        for c in right_containers:
            up = "Up" in c["status"]
            dot = '<span style="color:#4ade80">●</span>' if up else '<span style="color:#f87171">●</span>'
            st.markdown(f'<div class="cnt-card">{dot} <b>{c["name"]}</b> — {c["status"]}</div>',
                        unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Container IP Addresses")
    with st.spinner("Loading IPs..."):
        ips = get_ips()
    vlan_map = {
        "admin1":"VLAN10","admin2":"VLAN10",
        "hr1":"VLAN20","hr2":"VLAN20",
        "web1":"VLAN30/40",
        "srv1":"VLAN40",
        "acc1":"VLAN50","acc2":"VLAN50",
        "user1":"VLAN60","user2":"VLAN60","user3":"VLAN60","user4":"VLAN60",
        "user5":"VLAN60 (attacker)",
        "boss1":"VLAN70","boss2":"VLAN70","boss3":"VLAN70",
        "rtr-fw":"Gateway (all)"
    }
    rows = [{"Container": k, "IP": v, "Segment": vlan_map.get(k,"—")} for k,v in ips.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### iptables ACL Rules (rtr-fw)")
    rules = run("docker exec rtr-fw iptables -L FORWARD -n --line-numbers")
    if rules:
        st.code(rules, language="bash")
    else:
        st.warning("Cannot reach rtr-fw or ACL not applied")

# ═══════════════════════════════════════════════════════
# TAB 2 — Topology
# ═══════════════════════════════════════════════════════
with tab2:
    st.markdown("### Network Topology")

    vlans = [
        {"VLAN":"VLAN10","Subnet":"10.10.10.0/24","Gateway":"10.10.10.254",
         "Hosts":"admin1 (.10), admin2 (.11)","Role":"Administrators — full access to all segments"},
        {"VLAN":"VLAN20","Subnet":"10.10.20.0/24","Gateway":"10.10.20.254",
         "Hosts":"hr1 (.10), hr2 (.11)","Role":"HR — srv1 HTTP/SMB + internet only"},
        {"VLAN":"VLAN30","Subnet":"10.10.30.0/24","Gateway":"10.10.30.254",
         "Hosts":"web1 (.10)","Role":"DMZ — public web server"},
        {"VLAN":"VLAN40","Subnet":"10.10.40.0/24","Gateway":"10.10.40.254",
         "Hosts":"web1 (.10), srv1 (.10)","Role":"Server segment — internal file/web server"},
        {"VLAN":"VLAN50","Subnet":"10.10.50.0/24","Gateway":"10.10.50.254",
         "Hosts":"acc1 (.10), acc2 (.11)","Role":"Accounting — srv1 HTTP/SMB + internet only"},
        {"VLAN":"VLAN60","Subnet":"10.10.60.0/24","Gateway":"10.10.60.254",
         "Hosts":"user5 (.10), user1 (.11), user2 (.12), user3 (.13), user4 (.14)",
         "Role":"Users — DMZ HTTP + internet only"},
        {"VLAN":"VLAN70","Subnet":"10.10.70.0/24","Gateway":"10.10.70.254",
         "Hosts":"boss1 (.10), boss2 (.11), boss3 (.12)","Role":"Management — srv1 HTTP + internet only"},
    ]
    st.dataframe(pd.DataFrame(vlans), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Access Control List")
    st.caption("Allowed: yes | Blocked: no | Internet only: net")

    acl = {
        "Source \\ Destination": ["Admin(10)","HR(20)","DMZ(30)","Servers(40)","Accounting(50)","Users(60)","Management(70)"],
        "Admin(10)":       ["self","yes","yes","yes","yes","yes","yes"],
        "HR(20)":          ["no","self","no","yes HTTP/SMB","no","no","no"],
        "DMZ(30)":         ["no","no","self","no","no","no","no"],
        "Servers(40)":     ["no","no","no","self","no","no","no"],
        "Accounting(50)":  ["no","no","no","yes HTTP/SMB","self","no","no"],
        "Users(60)":       ["no","no","yes HTTP","no","no","self","no"],
        "Management(70)":  ["no","no","no","yes HTTP","no","no","self"],
    }
    df_acl = pd.DataFrame(acl).set_index("Source \\ Destination")
    st.dataframe(df_acl, use_container_width=True)

# ═══════════════════════════════════════════════════════
# TAB 3 — Traffic Tests
# ═══════════════════════════════════════════════════════
with tab3:
    st.markdown("### Traffic Tests — VLAN + ACL Scenarios")

    SCENARIOS = [
        # Group, from, to_ip, proto, desc, expect, url
        ("Same VLAN — always allowed",
         "hr1","10.10.20.11","ping","HR1 to HR2 (both VLAN20)",True,None),
        ("Same VLAN — always allowed",
         "acc1","10.10.50.11","ping","ACC1 to ACC2 (both VLAN50)",True,None),
        ("Same VLAN — always allowed",
         "user1","10.10.60.14","ping","USER1 to USER5 (both VLAN60)",True,None),

        ("Admin — full access (VLAN10)",
         "admin1","10.10.20.10","ping","Admin to HR1",True,None),
        ("Admin — full access (VLAN10)",
         "admin1","10.10.50.10","ping","Admin to ACC1",True,None),
        ("Admin — full access (VLAN10)",
         "admin1","10.10.40.10","ping","Admin to SRV1",True,None),
        ("Admin — full access (VLAN10)",
         "admin1","10.10.30.10","ping","Admin to WEB1 DMZ",True,None),
        ("Admin — full access (VLAN10)",
         "admin1","10.10.60.10","ping","Admin to USER5",True,None),
        ("Admin — full access (VLAN10)",
         "admin1","10.10.70.10","ping","Admin to BOSS1",True,None),

        ("Allowed HTTP — by ACL policy",
         "user1","10.10.30.10","http","Users HTTP to WEB1 DMZ (port 80)",True,"http://10.10.30.10"),
        ("Allowed HTTP — by ACL policy",
         "hr1","10.10.40.10","http","HR HTTP to SRV1 (port 80)",True,"http://10.10.40.10"),
        ("Allowed HTTP — by ACL policy",
         "acc1","10.10.40.10","http","Accounting HTTP to SRV1 (port 80)",True,"http://10.10.40.10"),
        ("Allowed HTTP — by ACL policy",
         "boss1","10.10.40.10","http","Management HTTP to SRV1 (port 80)",True,"http://10.10.40.10"),

        ("Blocked — cross-department ICMP",
         "hr1","10.10.50.10","ping","HR to Accounting — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "hr1","10.10.10.10","ping","HR to Admin — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "acc1","10.10.20.10","ping","Accounting to HR — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "acc1","10.10.10.10","ping","Accounting to Admin — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "boss1","10.10.20.10","ping","Management to HR — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "boss1","10.10.50.10","ping","Management to Accounting — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "user5","10.10.40.10","ping","Users to Servers — BLOCKED",False,None),
        ("Blocked — cross-department ICMP",
         "user5","10.10.10.10","ping","Users to Admin — BLOCKED",False,None),

        ("Blocked HTTP — policy violation",
         "hr1","10.10.50.10","http","HR HTTP to Accounting — BLOCKED",False,"http://10.10.50.10"),
        ("Blocked HTTP — policy violation",
         "user5","10.10.40.10","http","Users HTTP to Servers — BLOCKED",False,"http://10.10.40.10"),
        ("Blocked HTTP — policy violation",
         "user5","10.10.20.10","http","Users HTTP to HR — BLOCKED",False,"http://10.10.20.10"),
    ]

    groups = {}
    for s in SCENARIOS:
        g = s[0]
        groups.setdefault(g, []).append(s)

    # Manual single test
    st.markdown("#### Quick Manual Test")
    col_a, col_b, col_c, col_d = st.columns([2,2,2,1])
    all_containers = ["admin1","hr1","hr2","acc1","acc2","user1","user2","user3","user4","user5","boss1","boss2","boss3","web1","srv1"]
    with col_a:
        m_from = st.selectbox("From container", all_containers, key="m_from")
    with col_b:
        m_to = st.text_input("Target IP", "10.10.40.10", key="m_to")
    with col_c:
        m_proto = st.selectbox("Protocol", ["ping", "http"], key="m_proto")
    with col_d:
        st.markdown("<br>", unsafe_allow_html=True)
        run_manual = st.button("Run", key="m_run", use_container_width=True)

    if run_manual:
        with st.spinner("Testing..."):
            if m_proto == "ping":
                ok = ping_test(m_from, m_to)
                result_text = "PASS — reachable" if ok else "BLOCKED — no response"
                css = "r-pass" if ok else "r-block"
                raw = run(f"docker exec {m_from} ping -c 3 -W 2 {m_to}")
            else:
                ok, code = http_test(m_from, f"http://{m_to}")
                result_text = f"PASS — HTTP {code}" if ok else f"BLOCKED — HTTP {code}"
                css = "r-pass" if ok else "r-block"
                raw = run(f'docker exec {m_from} curl -v --connect-timeout 3 http://{m_to} 2>&1 | tail -6')
        st.markdown(f'<div class="result-row {css}"><b>{m_from} -> {m_to} [{m_proto}]:</b> {result_text}</div>', unsafe_allow_html=True)
        with st.expander("Raw output"):
            st.code(raw or "(no output)")

    st.markdown("---")
    st.markdown("#### Run All Scenario Groups")

    # Show each group as expandable section with Run button
    for group_name, group_tests in groups.items():
        with st.expander(f"  {group_name}  ({len(group_tests)} tests)", expanded=False):
            if st.button(f"Run: {group_name}", key=f"grp_{group_name}"):
                results_html = ""
                for _, frm, to_ip, proto, desc, expect, url in group_tests:
                    with st.spinner(f"{desc}..."):
                        if proto == "ping":
                            ok = ping_test(frm, to_ip)
                            got = "PASS" if ok else "BLOCK"
                        else:
                            ok, code = http_test(frm, url)
                            got = f"PASS HTTP {code}" if ok else f"BLOCK HTTP {code}"

                        correct = (ok == expect)
                        css = "r-pass" if (ok and expect) else ("r-block" if (not ok and not expect) else "r-fail")
                        marker = "PASS" if (ok and expect) else ("BLOCK" if (not ok and not expect) else "UNEXPECTED")
                        label = f"[{marker}] {frm} -> {to_ip} | {desc}"
                        results_html += f'<div class="result-row {css}">{label}</div>'

                st.markdown(results_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Run All Tests at Once")
    if st.button("Run all scenarios", use_container_width=True, key="run_all"):
        progress = st.progress(0)
        status_ph = st.empty()
        results_all = []

        for i, (grp, frm, to_ip, proto, desc, expect, url) in enumerate(SCENARIOS):
            status_ph.markdown(f"*Running: {desc}*")
            if proto == "ping":
                ok = ping_test(frm, to_ip)
                got = "PASS" if ok else "BLOCK"
            else:
                ok, code = http_test(frm, url)
                got = f"PASS HTTP {code}" if ok else f"BLOCK HTTP {code}"

            correct = (ok == expect)
            results_all.append({
                "Group": grp,
                "Test": desc,
                "From": frm,
                "Target": to_ip,
                "Expected": "PASS" if expect else "BLOCK",
                "Got": got,
                "OK": "Yes" if correct else "NO - check ACL"
            })
            progress.progress((i+1)/len(SCENARIOS))

        status_ph.empty()
        df_res = pd.DataFrame(results_all)
        passed = (df_res["OK"] == "Yes").sum()
        st.metric("Tests passed", f"{passed}/{len(SCENARIOS)}")
        st.dataframe(df_res, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Traffic Control")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("**Normal office traffic**")
        if st.button("Start background traffic", use_container_width=True):
            run("bash /home/Diploma/Traffic/generate_normal.sh")
            st.success("Office traffic started in background")
        if st.button("Stop all background traffic", use_container_width=True):
            for c in ["user1","user2","hr1","acc1","boss1"]:
                run(f"docker exec {c} pkill curl 2>/dev/null || true")
                run(f"docker exec {c} pkill ping 2>/dev/null || true")
            st.success("Traffic stopped")
    with col_t2:
        st.markdown("**ICMP Flood (for ACL demo)**")
        st.caption("Sends flood from user5 to srv1 to demonstrate ACL blocking")
        if st.button("Start ICMP flood (user5 -> srv1)", use_container_width=True):
            run("docker exec -d user5 ping -f -s 1400 10.10.40.10")
            st.warning("Flood started: user5 -> 10.10.40.10")
        if st.button("Stop ICMP flood", use_container_width=True):
            run("docker exec user5 pkill -9 ping 2>/dev/null || true")
            st.success("Flood stopped")

# ═══════════════════════════════════════════════════════
# TAB 4 — Logs
# ═══════════════════════════════════════════════════════
with tab4:
    st.markdown("### IPS Events Log")
    col_l1, col_l2 = st.columns([4,1])
    with col_l2:
        if st.button("Refresh", key="ref_log"):
            st.rerun()
        if st.button("Clear log", key="clr_log"):
            try:
                open("/home/Diploma/Traffic/ips_events.log","w").close()
                st.success("Cleared")
            except:
                st.error("Cannot clear")

    log_path = "/home/Diploma/Traffic/ips_events.log"
    if os.path.exists(log_path):
        with open(log_path) as f:
            content = f.read().strip()
        if content:
            lines = content.split("\n")
            st.metric("Events", len(lines))
            st.code("\n".join(reversed(lines[-60:])), language="bash")
        else:
            st.info("Log is empty")
    else:
        st.info("Log file not found")

    st.markdown("---")
    st.markdown("### iptables Live State")
    if st.button("Show iptables FORWARD", key="ipt_live"):
        rules = run("docker exec rtr-fw iptables -L FORWARD -n -v --line-numbers")
        st.code(rules or "No output / rtr-fw unreachable", language="bash")
