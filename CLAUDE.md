# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run both backend (port 9000) and frontend (port 8501)
make dev

# Run backend only
make backend

# Run frontend only
make frontend

# Kill processes on both ports
make clean
```

## Environment Setup

Create a `.env` file with:
```
ACS_CONNECTION_STRING="your_connection_string_here"
ACS_SENDER_EMAIL="DoNotReply@your-verified-domain.com"
```

## Architecture

This is a two-process application:

- **Backend** (`main.py`): FastAPI app exposing `POST /send-bulk-emails`. Accepts a multipart form with an HTML template file and an Excel file. Saves them to `uploads/`, then orchestrates bulk sending via `services/`.
- **Frontend** (`app.py`): Streamlit UI that calls the backend at `http://localhost:9000`.

### Services (`services/`)

| File | Responsibility |
|---|---|
| `excel_service.py` | Reads `.xlsx` with Polars into a `DataFrame` |
| `template_service.py` | Renders Jinja2 HTML templates against a row dict |
| `email_service.py` | Sends one email via Azure Communication Services SDK (synchronous `begin_send`, called in async context) |
| `batch_sender.py` | Orchestrates parallel sending: iterates the DataFrame in batches of 50, dispatches up to 10 concurrent tasks via `asyncio.Semaphore` |

### Data contract

The Excel file must have:
- `email` column — recipient address
- `subject` column — per-recipient email subject
- Any additional columns are available as Jinja2 template variables (e.g., `{{ first_name }}`)

### Known limitation

`email_service.py` uses the synchronous Azure SDK (`client.begin_send(...).result()`) inside an `async def`. This blocks the event loop. The semaphore limits concurrency but does not make the call non-blocking. For true async, migrate to `azure.communication.email.aio.EmailClient`.
