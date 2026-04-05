"""
app.py — Streamlit frontend
Pages:
  📧 Instant Send   — existing bulk email feature
  📅 Scheduler      — create & monitor scheduled campaigns
  📊 Dashboard      — overview of all campaigns
"""

import html
import json
import time
from datetime import date, datetime, timedelta

import polars as pl
import requests
import sseclient
import streamlit as st
import websocket

BACKEND = "http://localhost:9000"
WS_BACKEND = "ws://localhost:9000"

st.set_page_config(
    page_title="Email Automation",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global Styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"],
[data-testid="stHeader"], [data-testid="stToolbar"],
section[data-testid="stSidebar"], .stApp {
    background: #0a0c10 !important;
    color: #c8cdd8 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
[data-testid="stMain"] > div { background: #0a0c10 !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1017 !important;
    border-right: 1px solid #1e2430 !important;
}
section[data-testid="stSidebar"] * { font-family: 'IBM Plex Mono', monospace !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0d1017; }
::-webkit-scrollbar-thumb { background: #1e2430; border-radius: 3px; }

/* ── Page header ── */
.page-header {
    padding: 24px 0 8px;
    border-bottom: 1px solid #1e2430;
    margin-bottom: 28px;
}
.page-header h2 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.15rem;
    font-weight: 700;
    color: #e2e6f0;
    margin: 0;
    letter-spacing: 0.05em;
}
.page-header p { color: #5c6478; font-size: 0.85rem; margin: 4px 0 0; }

/* ── Stat cards ── */
.stat-row { display: flex; gap: 14px; margin: 16px 0 24px; }
.stat-card {
    flex: 1;
    background: #0d1017;
    border: 1px solid #1e2430;
    border-radius: 10px;
    padding: 16px 18px;
}
.stat-card .label { font-size: 0.72rem; color: #3d4558; font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px; }
.stat-card .value { font-size: 1.9rem; font-weight: 700; font-family: 'IBM Plex Mono', monospace; color: #e2e6f0; line-height: 1; }
.stat-card .value.green  { color: #3fb950; }
.stat-card .value.red    { color: #f85149; }
.stat-card .value.yellow { color: #d29922; }
.stat-card .value.blue   { color: #58a6ff; }

/* ── Window card ── */
.win-card {
    background: #0d1017;
    border: 1px solid #1e2430;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 8px 0;
    display: flex;
    align-items: center;
    gap: 16px;
}
.win-badge {
    background: #12171f;
    border: 1px solid #1e2430;
    border-radius: 6px;
    padding: 6px 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    color: #58a6ff;
    white-space: nowrap;
}
.win-meta { font-size: 0.8rem; color: #5c6478; }
.win-meta span { color: #c8cdd8; font-weight: 500; }

/* ── Campaign row ── */
.campaign-card {
    background: #0d1017;
    border: 1px solid #1e2430;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 10px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.campaign-name { font-weight: 600; color: #e2e6f0; font-size: 0.95rem; }
.campaign-meta { font-size: 0.78rem; color: #5c6478; font-family: 'IBM Plex Mono', monospace; margin-top: 3px; }
.pill {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    padding: 4px 10px;
    border-radius: 99px;
    font-weight: 600;
    border: 1px solid;
}
.pill-pending  { color: #8b949e; border-color: #30363d; background: #161b22; }
.pill-active   { color: #3fb950; border-color: #238636; background: #0d2016; }
.pill-paused   { color: #d29922; border-color: #9e6a03; background: #1a1700; }
.pill-done     { color: #58a6ff; border-color: #1f6feb; background: #031526; }
.pill-error    { color: #f85149; border-color: #6e1a18; background: #1c0a0a; }

/* ── Terminal ── */
.terminal {
    background: #060809;
    border: 1px solid #1e2430;
    border-radius: 10px;
    padding: 14px 16px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.77rem;
    line-height: 1.9;
    max-height: 280px;
    overflow-y: auto;
    color: #5c6478;
}
.terminal .ok  { color: #3fb950; }
.terminal .err { color: #f85149; }
.terminal .dim { color: #3d4558; }
.terminal .info { color: #58a6ff; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background: #1a2030 !important; border-radius: 99px !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #1f6feb, #58a6ff) !important;
    border-radius: 99px !important;
}

/* ── Metrics ── */
div[data-testid="metric-container"] {
    background: #0d1017 !important;
    border: 1px solid #1e2430 !important;
    border-radius: 10px !important;
    padding: 14px 16px 12px !important;
}
div[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; font-size: 1.8rem !important; color: #e2e6f0 !important; }
div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: #5c6478 !important; }

/* ── Input / Select ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input {
    background: #0d1017 !important;
    border-color: #1e2430 !important;
    color: #c8cdd8 !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-baseweb="select"] { background: #0d1017 !important; }

/* ── Buttons ── */
button[kind="primary"] {
    background: linear-gradient(180deg, #238636, #1a6128) !important;
    border: 1px solid #2ea043 !important;
    border-radius: 8px !important;
    color: #e2e6f0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
}
button[kind="secondary"] {
    background: #0d1017 !important;
    border: 1px solid #1e2430 !important;
    border-radius: 8px !important;
    color: #c8cdd8 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stDownloadButton"] button {
    background: #0d1017 !important;
    border: 1px solid #1e2430 !important;
    color: #58a6ff !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0d1017 !important;
    border: 1px dashed #1e2430 !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploader"] label { color: #5c6478 !important; font-family: 'IBM Plex Mono', monospace !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0d1017 !important;
    border: 1px solid #1e2430 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary { color: #c8cdd8 !important; font-family: 'IBM Plex Mono', monospace !important; }

/* ── Alerts ── */
[data-testid="stAlert"] { background: #0d1017 !important; border-radius: 10px !important; }
[data-testid="stAlertContentInfo"]    { border-left-color: #58a6ff !important; }
[data-testid="stAlertContentError"]   { border-left-color: #f85149 !important; }
[data-testid="stAlertContentSuccess"] { border-left-color: #3fb950 !important; }
[data-testid="stAlertContentWarning"] { border-left-color: #d29922 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #1e2430 !important; border-radius: 8px !important; }
[data-testid="stDataFrame"] * { color: #c8cdd8 !important; background: #0d1017 !important; }

/* ── Divider ── */
hr { border-color: #1e2430 !important; margin: 20px 0 !important; }

p, li { color: #c8cdd8 !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #3d4558 !important; }

/* ── Section label ── */
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3d4558;
    margin: 22px 0 10px;
    border-bottom: 1px solid #1e2430;
    padding-bottom: 6px;
}

/* ── Rate bar ── */
.rate-bar-wrap { margin: 8px 0 20px; }
.rate-bar-label { font-size: 0.8rem; color: #8b949e; margin-bottom: 6px; font-family: 'IBM Plex Mono', monospace; }
.rate-bar-bg { background: #1a2030; border: 1px solid #1e2430; border-radius: 99px; height: 20px; overflow: hidden; }
.rate-bar-fill {
    background: linear-gradient(90deg, #238636, #2ea043);
    height: 100%; border-radius: 99px;
    display: flex; align-items: center; padding-left: 10px;
    font-size: 0.72rem; color: #e2e6f0; font-weight: 700; min-width: 40px;
    font-family: 'IBM Plex Mono', monospace;
}

/* ── Info card ── */
.info-card {
    background: #0d1017;
    border: 1px solid #1e2430;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.83rem;
    color: #5c6478;
    margin: 6px 0 18px;
    font-family: 'IBM Plex Mono', monospace;
}
.info-card code { background: #12171f; color: #79c0ff; padding: 1px 5px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def api(method: str, path: str, **kwargs):
    try:
        r = requests.request(method, f"{BACKEND}{path}", **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot reach backend. Make sure it is running (`uvicorn main:app --port 9000`).")
        st.stop()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


STATUS_PILL = {
    "pending": '<span class="pill pill-pending">● pending</span>',
    "active":  '<span class="pill pill-active">● active</span>',
    "paused":  '<span class="pill pill-paused">● paused</span>',
    "done":    '<span class="pill pill-done">✓ done</span>',
    "error":   '<span class="pill pill-error">✗ error</span>',
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Sidebar
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='padding:20px 4px 24px;'>
        <div style='font-family:"IBM Plex Mono",monospace;font-size:1.05rem;font-weight:700;color:#e2e6f0;letter-spacing:0.05em;'>
            📧 EmailOps
        </div>
        <div style='font-size:0.72rem;color:#3d4558;margin-top:4px;font-family:"IBM Plex Mono",monospace;'>
            Bulk · Scheduled · Tracked
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["📧  Instant Send", "📅  Schedule Campaign", "📊  Dashboard"],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.68rem;color:#3d4558;font-family:\'IBM Plex Mono\',monospace;">Backend: localhost:9000</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — Instant Send
# ═══════════════════════════════════════════════════════════════════════════════

if "Instant" in page:
    st.markdown("""
    <div class='page-header'>
        <h2>📧 INSTANT BULK SEND</h2>
        <p>Upload template + recipient list and fire all emails now.</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns(2)
    with col_l:
        template_file = st.file_uploader("HTML Template (.html)", type=["html"],
                                          help="Jinja2 — use {{ variable }} for personalization")
    with col_r:
        excel_file = st.file_uploader("Recipient List (.xlsx)", type=["xlsx"],
                                       help="Must have 'email' and 'subject' columns")

    st.markdown("""
    <div class="info-card">
        Excel must have <code>email</code> and <code>subject</code> columns.
        Extra columns (e.g. <code>first_name</code>, <code>company</code>) become
        <code>{{ first_name }}</code> template variables.
    </div>
    """, unsafe_allow_html=True)

    ready = bool(template_file and excel_file)
    send_clicked = st.button("🚀  Send Now", type="primary", use_container_width=True, disabled=not ready)
    if not ready:
        st.caption("Upload both files to enable sending.")

    if send_clicked:
        files = {
            "template_file": (template_file.name, template_file, "text/html"),
            "excel_file": (excel_file.name, excel_file,
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        }
        with st.spinner("Uploading and starting job…"):
            try:
                res = requests.post(f"{BACKEND}/send-bulk-emails", files=files, timeout=30)
                res.raise_for_status()
            except requests.exceptions.ConnectionError:
                st.error("⚠️ Cannot reach backend.")
                st.stop()
            except Exception as e:
                st.error(f"Submission failed: {e}")
                st.stop()

        payload = res.json()
        job_id  = payload.get("job_id")
        total   = payload.get("total", 0)

        if not job_id:
            st.warning(payload.get("message", "Nothing to send."))
            st.stop()

        st.markdown(
            f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.8rem;color:#58a6ff;'
            f'background:#031526;border:1px solid #1f6feb;border-radius:6px;padding:6px 14px;'
            f'display:inline-block;margin-bottom:16px;">🔖 {job_id}  ·  {total:,} recipients</div>',
            unsafe_allow_html=True,
        )

        progress_bar = st.progress(0.0, text="Connecting…")
        st.markdown('<div class="section-label">Live Stats</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        sent_ph   = c1.empty(); failed_ph = c2.empty()
        remain_ph = c3.empty(); rate_ph   = c4.empty()
        timing_ph = st.empty()
        st.markdown('<div class="section-label">Activity Log</div>', unsafe_allow_html=True)
        log_ph    = st.empty()

        sent_ph.metric("✅ Sent", 0); failed_ph.metric("❌ Failed", 0)
        remain_ph.metric("⏳ Remaining", total); rate_ph.metric("⚡ Rate", "—")

        log_lines: list[str] = []
        all_results: list[dict] = []
        start = time.time()

        def _refresh(success, failed, done, elapsed):
            remaining = total - done
            rate = done / elapsed if elapsed > 0 else 0
            eta  = remaining / rate if rate > 0 else 0
            sent_ph.metric("✅ Sent", f"{success:,}")
            failed_ph.metric("❌ Failed", f"{failed:,}")
            remain_ph.metric("⏳ Remaining", f"{remaining:,}")
            rate_ph.metric("⚡ Rate", f"{rate:.1f}/s")
            parts = [f"⏱ {elapsed:.0f}s elapsed"]
            if eta > 0: parts.append(f"ETA ~{eta:.0f}s")
            timing_ph.caption("  ·  ".join(parts))

        def _push_log(email, status, error=None):
            safe = html.escape(email)
            if status == "success":
                log_lines.append(f'<span class="ok">✓ {safe}</span>')
            else:
                log_lines.append(f'<span class="err">✗ {safe}</span>  <span class="dim">→ {html.escape(error or "unknown")}</span>')
            log_ph.markdown(
                '<div class="terminal">' + "<br>".join(log_lines[-80:]) + "</div>",
                unsafe_allow_html=True,
            )

        ws = websocket.WebSocket()
        try:
            ws.connect(f"{WS_BACKEND}/ws/{job_id}")
            while True:
                raw = ws.recv()
                if not raw: break
                msg = json.loads(raw)
                if msg["type"] == "progress":
                    s = msg["success"]; f = msg["failed"]
                    elapsed = time.time() - start
                    pct = (s + f) / total
                    progress_bar.progress(pct, text=f"{s+f:,} / {total:,}  ({pct*100:.1f}%)")
                    _refresh(s, f, s + f, elapsed)
                    _push_log(msg["email"], msg["status"], msg.get("error"))
                    all_results.append({"email": msg["email"], "status": msg["status"], "error": msg.get("error", "")})
                elif msg["type"] == "complete":
                    elapsed = time.time() - start
                    progress_bar.progress(1.0, text=f"{total:,} / {total:,}  (100%)")
                    _refresh(msg["success"], msg["failed"], total, elapsed)
                    timing_ph.caption(f"⏱ Finished in {elapsed:.1f}s")
                    break
                elif msg["type"] == "error":
                    st.error(f"Job error: {html.escape(msg.get('detail', 'unknown'))}")
                    break
        except Exception as e:
            st.error(f"WebSocket error: {e}")
        finally:
            ws.close()

        if not all_results: st.stop()

        success_n = sum(1 for r in all_results if r["status"] == "success")
        failed_n  = len(all_results) - success_n
        rate_pct  = 100 * success_n / len(all_results) if all_results else 0

        st.markdown('<div class="section-label">Summary</div>', unsafe_allow_html=True)
        fa, fb, fc = st.columns(3)
        fa.metric("✅ Total Sent",      f"{success_n:,}")
        fb.metric("❌ Total Failed",    f"{failed_n:,}")
        fc.metric("📨 Total Processed", f"{len(all_results):,}")

        fill = max(rate_pct, 3)
        st.markdown(f"""
        <div class="rate-bar-wrap">
            <div class="rate-bar-label">Delivery Success Rate</div>
            <div class="rate-bar-bg">
                <div class="rate-bar-fill" style="width:{fill:.1f}%">{rate_pct:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        csv_bytes = pl.DataFrame(all_results).write_csv().encode("utf-8")
        st.download_button("📥 Download Results (CSV)", csv_bytes,
                           f"results_{job_id[:8]}.csv", "text/csv", use_container_width=True)

        failed_rows = [r for r in all_results if r["status"] == "failed"]
        if failed_rows:
            with st.expander(f"❌ Failed Emails ({len(failed_rows):,})", expanded=len(failed_rows) <= 20):
                st.dataframe(pl.DataFrame(failed_rows).drop("status"),
                             use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — Schedule Campaign
# ═══════════════════════════════════════════════════════════════════════════════

elif "Schedule" in page:
    st.markdown("""
    <div class='page-header'>
        <h2>📅 SCHEDULE CAMPAIGN</h2>
        <p>Define time windows, batches, and intervals — let the cron do the rest.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("schedule_form", clear_on_submit=False):
        st.markdown('<div class="section-label">Campaign Info</div>', unsafe_allow_html=True)
        col_name, col_day, col_tz = st.columns([3, 2, 2])
        campaign_name = col_name.text_input("Campaign Name", placeholder="e.g. May Newsletter")
        campaign_day  = col_day.date_input("Send Date", value=date.today())
        
        common_tzs = ["UTC", "Asia/Kolkata", "America/New_York", "Europe/London", "Asia/Dubai", "Australia/Sydney"]
        campaign_tz = col_tz.selectbox("Timezone", options=common_tzs, index=0)

        st.markdown('<div class="section-label">Files</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        tmpl_file  = c1.file_uploader("HTML Template", type=["html"], key="sched_tmpl")
        excel_file = c2.file_uploader("Recipient List (.xlsx)", type=["xlsx"], key="sched_xl")

        st.markdown("""
        <div class="info-card">
            Recipients will be distributed across your time windows in order.
            Make sure the sum of <code>Email Count</code> across windows ≤ total rows in your Excel.
        </div>
        """, unsafe_allow_html=True)

        # ── Time Windows Builder ──────────────────────────────────────────────
        st.markdown('<div class="section-label">Time Windows</div>', unsafe_allow_html=True)

        if "n_windows" not in st.session_state:
            st.session_state.n_windows = 1

        # Column headers shown once above all windows
        h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 3])
        h1.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;color:#5c6478;">🕐 Start Time<br><span style="color:#3d4558;font-size:0.65rem;">When to begin sending (HH:MM)</span></div>', unsafe_allow_html=True)
        h2.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;color:#5c6478;">🕗 End Time<br><span style="color:#3d4558;font-size:0.65rem;">When to stop sending (HH:MM)</span></div>', unsafe_allow_html=True)
        h3.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;color:#5c6478;">📦 Batch Size<br><span style="color:#3d4558;font-size:0.65rem;">Emails per batch (e.g. 70)</span></div>', unsafe_allow_html=True)
        h4.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;color:#5c6478;">⏱ Interval (secs)<br><span style="color:#3d4558;font-size:0.65rem;">Wait between batches (e.g. 120)</span></div>', unsafe_allow_html=True)
        h5.markdown('<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;color:#5c6478;">✉️ Email Count<br><span style="color:#3d4558;font-size:0.65rem;">Recipients assigned to this window</span></div>', unsafe_allow_html=True)

        windows_data = []
        for i in range(st.session_state.n_windows):
            st.markdown(
                f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:0.7rem;'
                f'color:#3d4558;margin:10px 0 2px;border-left:2px solid #1e2430;padding-left:8px;">'
                f'Window {i+1}</div>',
                unsafe_allow_html=True,
            )
            w_cols = st.columns([2, 2, 2, 2, 3])
            start_t  = w_cols[0].text_input("Start Time",     value="09:00", key=f"w_start_{i}", label_visibility="collapsed", placeholder="e.g. 14:00")
            end_t    = w_cols[1].text_input("End Time",       value="10:00", key=f"w_end_{i}",   label_visibility="collapsed", placeholder="e.g. 15:00")
            b_size   = w_cols[2].number_input("Batch Size",   min_value=1, max_value=500, value=70,  key=f"w_bsize_{i}", label_visibility="collapsed", help="How many emails to send in one shot. Recommended: 50–100 to stay within rate limits.")
            interval = w_cols[3].number_input("Interval (s)", min_value=10, max_value=3600, value=120, key=f"w_int_{i}", label_visibility="collapsed", help="Seconds to wait before firing the next batch. 120 s (2 min) is a safe default. Intervals are randomised ±20% automatically.")
            em_count = w_cols[4].number_input("Email Count",  min_value=1, value=500, key=f"w_ecount_{i}", label_visibility="collapsed", help="Total recipients assigned to this window. Sum across all windows must not exceed your Excel row count.")
            windows_data.append({
                "start_time": start_t, "end_time": end_t,
                "batch_size": int(b_size), "interval_secs": int(interval),
                "email_count": int(em_count),
            })

        add_win_col, _, submit_col = st.columns([2, 3, 2])

        submitted = submit_col.form_submit_button("✅  Create Schedule", type="primary", use_container_width=True)

    # + Window button outside form
    if st.button("＋ Add Window", use_container_width=False):
        st.session_state.n_windows += 1
        st.rerun()
    if st.session_state.n_windows > 1:
        if st.button("－ Remove Last", use_container_width=False):
            st.session_state.n_windows -= 1
            st.rerun()

    if submitted:
        if not campaign_name:
            st.error("Campaign name is required.")
        elif not tmpl_file or not excel_file:
            st.error("Both template and Excel files are required.")
        else:
            # Each field sent as a separate named form field — matches
            # FastAPI Form(...) parameters exactly, no encoding ambiguity.
            files = {
                "template_file": (tmpl_file.name, tmpl_file, "text/html"),
                "excel_file": (excel_file.name, excel_file,
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            }
            form_data = {
                "name":    campaign_name,
                "day":     str(campaign_day),
                "timezone": campaign_tz,
                "windows": json.dumps(windows_data),   # JSON-encoded list
            }

            # ── Frontend validation before hitting the API ────────────────
            fe_errors = []
            total_email_count = sum(w["email_count"] for w in windows_data)
            if total_email_count == 0:
                fe_errors.append("Total email count across all windows is 0.")
            for idx, w in enumerate(windows_data):
                if w["start_time"] >= w["end_time"]:
                    fe_errors.append(f"Window {idx+1}: Start time must be before end time.")
                if w["batch_size"] < 1:
                    fe_errors.append(f"Window {idx+1}: Batch size must be at least 1.")
                if w["interval_secs"] < 10:
                    fe_errors.append(f"Window {idx+1}: Interval must be at least 10 seconds.")

            if fe_errors:
                for err in fe_errors:
                    st.error(f"⚠️ {err}")
            else:
                with st.spinner("Creating schedule…"):
                    try:
                        res = requests.post(
                            f"{BACKEND}/schedules",
                            files=files,
                            data=form_data,
                            timeout=30,
                        )
                        # Extract the real FastAPI error detail instead of
                        # showing the generic "422 Client Error" requests message
                        if not res.ok:
                            try:
                                err_body = res.json()
                                # FastAPI wraps validation errors as {"detail": [...]}
                                detail = err_body.get("detail", res.text)
                                if isinstance(detail, list):
                                    # Pydantic validation errors — list of {loc, msg, type}
                                    messages = [
                                        f"Field `{'→'.join(str(x) for x in e.get('loc', []))}`: {e.get('msg', e)}"
                                        for e in detail
                                    ]
                                    st.error("❌ Validation errors from server:")
                                    for m in messages:
                                        st.error(f"  • {m}")
                                else:
                                    st.error(f"❌ Server error ({res.status_code}): {detail}")
                            except Exception:
                                st.error(f"❌ Server error ({res.status_code}): {res.text[:500]}")
                        else:
                            result = res.json()
                            st.success(
                                f"✅ Schedule created!  "
                                f"`{result['schedule_id']}`  |  "
                                f"{result['total_emails']:,} emails  |  "
                                f"{result['windows']} window(s)  |  "
                                f"{result['excel_rows']:,} Excel rows loaded"
                            )
                            st.session_state.n_windows = 1
                    except requests.exceptions.ConnectionError:
                        st.error("⚠️ Cannot reach backend. Make sure it is running (`uvicorn main:app --port 9000`).")
                    except requests.exceptions.Timeout:
                        st.error("⚠️ Request timed out. The Excel file may be very large — try again.")
                    except Exception as exc:
                        st.error(f"❌ Unexpected error: {exc}")

    # ── Monitor live schedule ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-label">Monitor a Schedule (Live)</div>', unsafe_allow_html=True)

    schedules = api("GET", "/schedules") or []
    active    = [s for s in schedules if s["status"] in ("pending", "active")]

    if not active:
        st.caption("No active schedules found. Create one above.")
    else:
        opts = {f"{s['name']}  [{s['status']}]  {s['day']}": s["id"] for s in active}
        sel  = st.selectbox("Choose schedule to monitor", list(opts.keys()))
        if sel:
            sched_id = opts[sel]
            monitor_btn = st.button("📡  Connect Live Feed", type="primary")

            if monitor_btn:
                detail = api("GET", f"/schedules/{sched_id}") or {}
                total_em = detail.get("total_emails", 0)

                log_ph2   = st.empty()
                status_ph = st.empty()
                log2: list[str] = []

                def _push2(msg: str, cls="dim"):
                    log2.append(f'<span class="{cls}">{html.escape(msg)}</span>')
                    log_ph2.markdown(
                        '<div class="terminal">' + "<br>".join(log2[-60:]) + "</div>",
                        unsafe_allow_html=True,
                    )

                _push2(f"Connecting to schedule {sched_id}…", "info")

                try:
                    stream_res = requests.get(
                        f"{BACKEND}/schedules/{sched_id}/stream",
                        stream=True, timeout=None,
                    )
                    client = sseclient.SSEClient(stream_res)
                    for event in client.events():
                        if not event.data or event.data.strip() == "": continue
                        ev = json.loads(event.data)
                        t  = ev.get("type")
                        if t == "progress":
                            status = ev.get("status", "?")
                            email  = ev.get("email", "?")
                            batch  = ev.get("batch", "?")
                            win    = ev.get("window", "")
                            cls    = "ok" if status == "sent" else "err"
                            _push2(f"[batch {batch}] [{win}] {email} → {status}", cls)
                        elif t == "batch_done":
                            _push2(
                                f"Batch {ev['batch']}/{ev['max_batch']} done — "
                                f"sent={ev['sent']} failed={ev['failed']}  next≈{ev.get('next_at','?')[:16]}",
                                "info",
                            )
                        elif t == "schedule_done":
                            _push2("🎉 Schedule complete!", "ok")
                            status_ph.success("Schedule complete!")
                            break
                except Exception as e:
                    st.error(f"Stream error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

elif "Dashboard" in page:
    st.markdown("""
    <div class='page-header'>
        <h2>📊 CAMPAIGN DASHBOARD</h2>
        <p>All scheduled campaigns, status, and batch logs.</p>
    </div>
    """, unsafe_allow_html=True)

    col_refresh, col_spacer = st.columns([1, 5])
    if col_refresh.button("🔄  Refresh", use_container_width=True):
        st.rerun()

    schedules = api("GET", "/schedules") or []

    if not schedules:
        st.info("No campaigns yet. Create one in the **Schedule Campaign** tab.")
    else:
        # Summary row
        total_s = sum(s.get("sent_count", 0)    for s in schedules)
        total_f = sum(s.get("failed_count", 0)  for s in schedules)
        total_p = sum(s.get("pending_count", 0) for s in schedules)
        total_e = sum(s.get("total_emails", 0)  for s in schedules)

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card"><div class="label">Campaigns</div><div class="value blue">{len(schedules)}</div></div>
            <div class="stat-card"><div class="label">Sent</div><div class="value green">{total_s:,}</div></div>
            <div class="stat-card"><div class="label">Failed</div><div class="value red">{total_f:,}</div></div>
            <div class="stat-card"><div class="label">Pending</div><div class="value yellow">{total_p:,}</div></div>
            <div class="stat-card"><div class="label">Total Queued</div><div class="value">{total_e:,}</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">Campaigns</div>', unsafe_allow_html=True)

        for sched in schedules:
            status_html = STATUS_PILL.get(sched["status"], sched["status"])
            sent_n    = sched.get("sent_count", 0)
            failed_n  = sched.get("failed_count", 0)
            pending_n = sched.get("pending_count", 0)
            total_n   = sched.get("total_emails", 0)
            pct       = round(100 * sent_n / total_n) if total_n else 0

            st.markdown(f"""
            <div class="campaign-card">
                <div style="flex:1;">
                    <div class="campaign-name">{html.escape(sched['name'])}</div>
                    <div class="campaign-meta">{sched['day']}  ·  id: {sched['id'][:8]}…</div>
                </div>
                <div style="text-align:right;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:#8b949e;">
                    <div><span style="color:#3fb950">{sent_n:,}</span> sent &nbsp;
                         <span style="color:#f85149">{failed_n:,}</span> failed &nbsp;
                         <span style="color:#d29922">{pending_n:,}</span> pending</div>
                    <div style="margin-top:4px;">{pct}% complete</div>
                </div>
                <div>{status_html}</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"Details — {sched['name']}", expanded=False):
                detail = api("GET", f"/schedules/{sched['id']}") or {}
                windows = detail.get("windows", [])

                if windows:
                    st.markdown('<div class="section-label" style="margin-top:4px;">Time Windows</div>', unsafe_allow_html=True)
                    for w in windows:
                        w_sent    = 0  # could add per-window query
                        w_status  = STATUS_PILL.get(w["status"], w["status"])
                        st.markdown(f"""
                        <div class="win-card">
                            <div class="win-badge">{w['start_time']} → {w['end_time']}</div>
                            <div class="win-meta">
                                batch size <span>{w['batch_size']}</span> &nbsp;·&nbsp;
                                interval <span>{w['interval_secs']}s</span> &nbsp;·&nbsp;
                                emails <span>{w['email_count']:,}</span> &nbsp;·&nbsp;
                                batches sent <span>{w['batches_sent']}</span>
                            </div>
                            <div style="margin-left:auto;">{w_status}</div>
                        </div>
                        """, unsafe_allow_html=True)

                # Batch log
                logs = api("GET", f"/schedules/{sched['id']}/logs") or []
                if logs:
                    st.markdown('<div class="section-label">Recent Batch Logs</div>', unsafe_allow_html=True)
                    log_df = pl.DataFrame(logs).select([
                        "batch_number", "start_time", "end_time",
                        "emails_sent", "emails_failed", "executed_at", "next_batch_at",
                    ])
                    st.dataframe(log_df, use_container_width=True, hide_index=True)

                # Action buttons
                btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1, 1, 3])
                if sched["status"] == "paused":
                    if btn_col1.button("▶  Activate", key=f"act_{sched['id']}"):
                        api("POST", f"/schedules/{sched['id']}/activate")
                        st.rerun()
                elif sched["status"] == "active":
                    if btn_col1.button("⏸  Pause", key=f"pause_{sched['id']}"):
                        api("POST", f"/schedules/{sched['id']}/pause")
                        st.rerun()

                if btn_col2.button("🗑  Delete", key=f"del_{sched['id']}"):
                    api("DELETE", f"/schedules/{sched['id']}")
                    st.rerun()