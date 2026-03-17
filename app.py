
import html
import json
import time
import streamlit as st
import requests
import websocket

BACKEND    = "http://localhost:9000"
WS_BACKEND = "ws://localhost:9000"

st.set_page_config(
    page_title="Bulk Email Sender",
    page_icon="📧",
    layout="centered",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
section[data-testid="stSidebar"],
.stApp { background: #0d1117 !important; color: #c9d1d9 !important; }

[data-testid="stMain"] > div { background: #0d1117 !important; }

/* scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #161b22; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #1f2d5a 0%, #2d1f5a 100%);
    border: 1px solid #30363d;
    border-radius: 16px;
    padding: 36px 32px 28px;
    text-align: center;
    margin-bottom: 28px;
}
.hero h1 { color: #e6edf3; margin: 0 0 8px; font-size: 2rem; letter-spacing: -0.5px; }
.hero p  { color: #8b949e; margin: 0; font-size: 1rem; }

/* ── Info card ── */
.info-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 4px solid #58a6ff;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #8b949e;
    margin: 4px 0 20px;
}
.info-card code {
    background: #1f2937;
    color: #79c0ff;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.85em;
}

/* ── Job pill ── */
.job-pill {
    display: inline-block;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 99px;
    padding: 5px 14px;
    font-family: monospace;
    font-size: 0.8rem;
    color: #79c0ff;
    margin-bottom: 18px;
}

/* ── Section label ── */
.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #484f58;
    margin: 20px 0 8px;
}

/* ── Terminal log ── */
.terminal {
    background: #010409;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px 18px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 0.78rem;
    line-height: 1.8;
    max-height: 300px;
    overflow-y: auto;
    color: #8b949e;
}
.terminal .ok  { color: #3fb950; }
.terminal .err { color: #f85149; }
.terminal .dim { color: #484f58; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background: #21262d !important;
    border-radius: 99px !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, #1f6feb, #58a6ff) !important;
    border-radius: 99px !important;
}

/* ── Rate bar ── */
.rate-bar-wrap { margin: 6px 0 20px; }
.rate-bar-label { font-size: 0.82rem; color: #8b949e; margin-bottom: 6px; }
.rate-bar-bg {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 99px;
    height: 22px;
    overflow: hidden;
}
.rate-bar-fill {
    background: linear-gradient(90deg, #238636, #2ea043);
    height: 100%;
    border-radius: 99px;
    display: flex;
    align-items: center;
    padding-left: 10px;
    font-size: 0.75rem;
    color: #e6edf3;
    font-weight: 700;
    min-width: 42px;
}

/* ── Summary card ── */
.summary-card {
    border-radius: 12px;
    padding: 20px 24px;
    margin: 20px 0 12px;
}
.summary-ok {
    background: #0d1117;
    border: 1px solid #238636;
    border-left: 5px solid #2ea043;
    color: #3fb950;
}
.summary-warn {
    background: #0d1117;
    border: 1px solid #9e6a03;
    border-left: 5px solid #d29922;
    color: #e3b341;
}
.summary-card strong { color: #e6edf3; }

/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
    padding: 18px 14px 14px !important;
}
div[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700 !important;
    color: #e6edf3 !important;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    color: #8b949e !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #161b22 !important;
    border: 1px dashed #30363d !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploader"] label { color: #8b949e !important; }
[data-testid="stFileUploaderDropzone"] { background: #161b22 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { color: #8b949e !important; }

/* ── Buttons ── */
button[kind="primary"] {
    background: linear-gradient(180deg, #238636, #1a6128) !important;
    border: 1px solid #2ea043 !important;
    border-radius: 8px !important;
    color: #e6edf3 !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(180deg, #2ea043, #238636) !important;
}
button[kind="secondary"] {
    background: #21262d !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    color: #c9d1d9 !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #21262d !important;
    border: 1px solid #30363d !important;
    color: #79c0ff !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary { color: #c9d1d9 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #30363d !important; border-radius: 8px !important; }
[data-testid="stDataFrame"] * { color: #c9d1d9 !important; }
.dvn-scroller { background: #161b22 !important; }

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: #161b22 !important;
    border-radius: 10px !important;
}
[data-testid="stAlertContentInfo"]    { border-left-color: #58a6ff !important; }
[data-testid="stAlertContentError"]   { border-left-color: #f85149 !important; }
[data-testid="stAlertContentWarning"] { border-left-color: #d29922 !important; }
[data-testid="stAlertContentSuccess"] { border-left-color: #2ea043 !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] p { color: #8b949e !important; }

/* ── Caption / text ── */
.stCaption, [data-testid="stCaptionContainer"] { color: #484f58 !important; }
p, li { color: #c9d1d9 !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>📧 Bulk Email Sender</h1>
    <p>Send personalised emails at scale via Azure Communication Services</p>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)
with col_l:
    template_file = st.file_uploader(
        "HTML Template",
        type=["html"],
        help="Jinja2 template — use {{ variable }} for dynamic fields",
    )
with col_r:
    excel_file = st.file_uploader(
        "Recipient List (.xlsx)",
        type=["xlsx"],
        help="Must have 'email' and 'subject' columns",
    )

st.markdown("""
<div class="info-card">
    📋 Excel must have <code>email</code> and <code>subject</code> columns.
    Any extra columns (e.g. <code>first_name</code>, <code>company</code>)
    become available as <code>{{ first_name }}</code> template variables.
</div>
""", unsafe_allow_html=True)

ready = bool(template_file and excel_file)
send_clicked = st.button(
    "🚀  Send Emails",
    type="primary",
    use_container_width=True,
    disabled=not ready,
)

if not ready:
    st.caption("Upload both files above to enable sending.")

# ── Main logic ────────────────────────────────────────────────────────────────
if send_clicked:

    # Step 1 – submit ──────────────────────────────────────────────────────────
    files = {
        "template_file": (template_file.name, template_file, "text/html"),
        "excel_file": (
            excel_file.name,
            excel_file,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }

    with st.spinner("Uploading files and starting job…"):
        try:
            res = requests.post(f"{BACKEND}/send-bulk-emails", files=files, timeout=30)
            res.raise_for_status()
        except requests.exceptions.ConnectionError:
            st.error("⚠️ Cannot reach backend. Make sure it's running (`make dev`).")
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

    # Step 2 – stream progress ─────────────────────────────────────────────────
    st.markdown(
        f'<div class="job-pill">🔖 {job_id} &nbsp;·&nbsp; {total:,} recipients</div>',
        unsafe_allow_html=True,
    )

    progress_bar = st.progress(0.0, text="Waiting for first response…")

    st.markdown('<div class="section-label">Live Stats</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    sent_ph    = c1.empty()
    failed_ph  = c2.empty()
    remain_ph  = c3.empty()
    rate_ph    = c4.empty()

    timing_ph  = st.empty()

    st.markdown('<div class="section-label">Activity Log</div>', unsafe_allow_html=True)
    log_ph     = st.empty()

    # Render initial zeroed metrics
    sent_ph.metric("✅ Sent",       0)
    failed_ph.metric("❌ Failed",   0)
    remain_ph.metric("⏳ Remaining", total)
    rate_ph.metric("⚡ Rate",       "—")

    log_lines:   list[str]  = []
    all_results: list[dict] = []
    start_time  = time.time()

    def _refresh(success: int, failed: int, done: int, elapsed: float):
        remaining = total - done
        rate      = done / elapsed if elapsed > 0 else 0
        eta_s     = remaining / rate if rate > 0 else 0

        sent_ph.metric("✅ Sent",        f"{success:,}")
        failed_ph.metric("❌ Failed",    f"{failed:,}")
        remain_ph.metric("⏳ Remaining", f"{remaining:,}")
        rate_ph.metric("⚡ Rate",        f"{rate:.1f}/s")

        parts = [f"⏱ {elapsed:.0f}s elapsed"]
        if eta_s > 0:
            parts.append(f"ETA ~{eta_s:.0f}s")
        timing_ph.caption("  ·  ".join(parts))

    def _push_log(email: str, status: str, error: str | None):
        safe_email = html.escape(email)
        if status == "success":
            line = f'<span class="ok">✓ {safe_email}</span>'
        else:
            safe_err = html.escape(error or "unknown error")
            line = f'<span class="err">✗ {safe_email}</span>  <span class="dim">→ {safe_err}</span>'
        log_lines.append(line)
        log_ph.markdown(
            '<div class="terminal">' + "<br>".join(log_lines[-80:]) + "</div>",
            unsafe_allow_html=True,
        )

    # WebSocket receive loop
    ws = websocket.WebSocket()
    try:
        ws.connect(f"{WS_BACKEND}/ws/{job_id}")

        while True:
            raw = ws.recv()
            if not raw:
                break
            msg = json.loads(raw)

            if msg["type"] == "progress":
                success = msg["success"]
                failed  = msg["failed"]
                done    = success + failed
                elapsed = time.time() - start_time

                pct  = done / total
                progress_bar.progress(pct, text=f"{done:,} / {total:,}  ({pct*100:.1f}%)")
                _refresh(success, failed, done, elapsed)
                _push_log(msg["email"], msg["status"], msg.get("error"))

                all_results.append({
                    "email":  msg["email"],
                    "status": msg["status"],
                    "error":  msg.get("error", ""),
                })

            elif msg["type"] == "complete":
                elapsed = time.time() - start_time
                progress_bar.progress(1.0, text=f"{total:,} / {total:,}  (100%)")
                _refresh(msg["success"], msg["failed"], total, elapsed)
                timing_ph.caption(f"⏱ Finished in {elapsed:.1f}s")
                break

            elif msg["type"] == "error":
                st.error(f"❌ Job error: {html.escape(msg.get('detail', 'Unknown error'))}")
                break

    except Exception as e:
        st.error(f"WebSocket error: {e}")
    finally:
        ws.close()

    # Step 3 – summary ─────────────────────────────────────────────────────────
    if not all_results:
        st.stop()

    import polars as pl

    success_n = sum(1 for r in all_results if r["status"] == "success")
    failed_n  = len(all_results) - success_n
    rate_pct  = 100 * success_n / len(all_results) if all_results else 0

    card_cls  = "summary-ok" if failed_n == 0 else "summary-warn"
    icon      = "🎉" if failed_n == 0 else "⚠️"
    st.markdown(f"""
<div class="summary-card {card_cls}">
    <strong>{icon} Job complete</strong> &nbsp;—&nbsp;
    <strong>{success_n:,}</strong> sent,
    <strong>{failed_n:,}</strong> failed
    out of <strong>{len(all_results):,}</strong> total.
</div>
""", unsafe_allow_html=True)

    # Success-rate bar
    fill = max(rate_pct, 3)  # keep label readable even at low %
    st.markdown(f"""
<div class="rate-bar-wrap">
    <div class="rate-bar-label">Delivery Success Rate</div>
    <div class="rate-bar-bg">
        <div class="rate-bar-fill" style="width:{fill:.1f}%">
            {rate_pct:.1f}%
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    # Final stat row
    fa, fb, fc = st.columns(3)
    fa.metric("✅ Total Sent",  f"{success_n:,}")
    fb.metric("❌ Total Failed", f"{failed_n:,}")
    fc.metric("📨 Total Processed", f"{len(all_results):,}")

    st.write("")

    # Download results
    csv_bytes = pl.DataFrame(all_results).write_csv().encode("utf-8")
    st.download_button(
        label="📥 Download Full Results (CSV)",
        data=csv_bytes,
        file_name=f"email_results_{job_id[:8]}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Failed email detail
    failed_rows = [r for r in all_results if r["status"] == "failed"]
    if failed_rows:
        st.write("")
        with st.expander(f"❌  Failed Emails  ({len(failed_rows):,})", expanded=len(failed_rows) <= 20):
            st.dataframe(
                pl.DataFrame(failed_rows).drop("status"),
                use_container_width=True,
                hide_index=True,
            )
