# 📧 Email Automation System (Azure Communication Services)

A high-performance bulk email platform built with FastAPI, Streamlit, and Polars. Send thousands of emails instantly or schedule them across smart time windows — with full SQLite tracking and live progress.

## Features

- **Instant Bulk Send** — fire all emails now with live WebSocket progress and downloadable results
- **Scheduled Campaigns** — define multiple time windows per day (e.g. light warm-up at 2 PM, heavy push at 7 PM)
- **Cron-based Auto-sender** — APScheduler ticks every 60 s, respects your windows, fires batches automatically
- **SQLite Queue Tracking** — every email, batch, and window is persisted; full audit trail
- **Resumable** — restart the server anytime; the scheduler picks up from the last sent batch
- **Jitter + Rate Safety** — batch intervals randomized ±20% to protect sender reputation
- **Parallel Processing** — async concurrency with semaphore control for maximum throughput
- **Polars Integration** — lightning-fast Excel parsing and data handling
- **Jinja2 Templating** — full dynamic HTML templates with per-recipient variables
- **Azure Communication Services** — enterprise-grade email delivery

## Prerequisites

- [uv](https://github.com/astral-sh/uv) installed
- Azure Communication Services resource (Connection String + Verified Sender Domain)
- Python 3.12+

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd email-sender
```

### 2. Environment variables

```bash
cp .env.example .env
```

Fill in your Azure details:

```env
ACS_CONNECTION_STRING="your_connection_string_here"
ACS_SENDER_EMAIL="DoNotReply@your-verified-domain.com"
```

### 3. Install dependencies

```bash
uv sync
```

## Running

```bash
make dev
```

- **Backend (FastAPI)** → `http://localhost:9000`
- **Frontend (Streamlit)** → `http://localhost:8501`

## Pages

### 📧 Instant Send
Upload an HTML template and Excel file → click **Send Now** → watch live per-email progress stream in. Download a full CSV report when done.

### 📅 Schedule Campaign
1. Set a campaign name and date
2. Add one or more **time windows** — each with its own start/end time, batch size, interval (seconds), and email count
3. Upload template + Excel → the queue is built and saved to SQLite
4. The backend cron fires every 60 s, checks the current time against your windows, and sends the next due batch automatically

### 📊 Dashboard
- Summary stats across all campaigns (sent, failed, pending)
- Per-campaign breakdown with window details and batch logs
- Activate, pause, or delete any campaign

## Excel Format

| email | subject | first_name | company |
|---|---|---|---|
| alice@example.com | Hello from us! | Alice | Acme |
| bob@example.com | Hello from us! | Bob | Globex |

`email` and `subject` are required. All other columns are available as `{{ variable }}` in your HTML template.

## How the Scheduler Works

```
Every 60 seconds:
  For each active schedule matching today's date:
    For each time window:
      If current time is inside the window:
        Read batch_log → find last batch sent + next_batch_at
        If now >= next_batch_at (±20% jitter):
          Fetch next pending batch from email_queue
          Send via Azure → mark sent/failed
          Write to batch_log → schedule next batch time
```

## Project Structure

```
email-sender/
├── main.py                     # FastAPI — all API + WebSocket + SSE endpoints
├── app.py                      # Streamlit — 3-page frontend
├── Makefile
├── pyproject.toml
├── .env
└── services/
    ├── db.py                   # SQLite schema + all queries
    ├── scheduler_service.py    # APScheduler cron (60 s tick)
    ├── batch_sender.py         # Async instant bulk sender
    ├── email_service.py        # Azure ACS send wrapper
    ├── excel_service.py        # Polars Excel reader
    └── template_service.py     # Jinja2 renderer
```

---

## ⚠️ Security Warning: Git Secret Leak

If you accidentally committed your `.env` file, act immediately:

1. **Remove `.env` from git tracking**:
   ```bash
   git rm --cached .env
   git commit -m "fix: remove sensitive .env from git tracking"
   ```

2. **Rotate your keys** — go to the Azure Portal and **regenerate your keys** right away if the connection string was ever pushed.

3. **Rewrite history** (recommended) — use [`git-filter-repo`](https://github.com/newren/git-filter-repo) to permanently remove the secret from all past commits.

4. **GitHub push protection** — if GitHub blocked your push, do not bypass it. Fix the commit first.