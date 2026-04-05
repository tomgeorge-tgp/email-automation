"""
main.py — FastAPI backend
  • POST /send-bulk-emails          (existing instant send)
  • GET  /ws/{job_id}               (existing WebSocket progress)
  • POST /schedules                 (create scheduled campaign)
  • GET  /schedules                 (list all)
  • GET  /schedules/{id}            (detail + windows)
  • DELETE /schedules/{id}          (delete)
  • GET  /schedules/{id}/logs       (batch log)
  • GET  /schedules/{id}/stream     (SSE live updates)
  • POST /schedules/{id}/activate   (manually activate)
  • POST /schedules/{id}/pause      (pause)
"""

import asyncio
import json
import math
import os
import shutil
import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.excel_service import read_excel
from services.batch_sender import send_bulk_emails
from services.template_service import render_template
from services.db import (
    init_db,
    create_schedule,
    add_time_window,
    bulk_insert_emails,
    get_all_schedules,
    get_schedule,
    get_windows,
    get_batch_logs,
    delete_schedule,
    update_schedule_status,
)
from services.scheduler_service import (
    start_scheduler,
    register_listener,
    unregister_listener,
)

app = FastAPI(title="Email Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)

# In-memory job store for instant-send jobs
jobs: dict[str, dict] = {}


@app.on_event("startup")
async def startup():
    init_db()
    start_scheduler()


@app.get("/health")
async def health_check():
    return {"status": "new health check"}


# ══════════════════════════════════════════════════════════════════════════════
#  Instant bulk send (existing)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/send-bulk-emails")
async def send_bulk_emails_api(
    template_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
):
    template_path = f"uploads/{template_file.filename}"
    excel_path    = f"uploads/{excel_file.filename}"

    with open(template_path, "wb") as f:
        shutil.copyfileobj(template_file.file, f)
    with open(excel_path, "wb") as f:
        shutil.copyfileobj(excel_file.file, f)

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    users_df = read_excel(excel_path)
    if len(users_df) == 0:
        return {"job_id": None, "total": 0, "message": "No users found."}

    job_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    jobs[job_id] = {"queue": queue, "status": "running", "total": len(users_df)}

    asyncio.create_task(_run_job(job_id, template_str, users_df, queue))
    return {"job_id": job_id, "total": len(users_df)}


async def _run_job(job_id, template_str, users_df, queue):
    try:
        await send_bulk_emails(template_str=template_str, users_df=users_df,
                                concurrency=10, batch_size=50, queue=queue)
        jobs[job_id]["status"] = "complete"
    except Exception:
        jobs[job_id]["status"] = "error"


@app.websocket("/ws/{job_id}")
async def ws_endpoint(websocket: WebSocket, job_id: str):
    if job_id not in jobs:
        await websocket.close(code=4004)
        return
    await websocket.accept()
    queue = jobs[job_id]["queue"]
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            queue.task_done()
            if event["type"] in ("complete", "error"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
        jobs.pop(job_id, None)


# ══════════════════════════════════════════════════════════════════════════════
#  Scheduled campaigns
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/schedules")
async def create_schedule_api(
    name: str    = Form(..., description="Campaign display name"),
    day: str     = Form(..., description="Send date as YYYY-MM-DD"),
    windows: str = Form(..., description="JSON array of window objects"),
    timezone: str = Form("UTC", description="Timezone name, e.g. Asia/Kolkata"),
    template_file: UploadFile = File(...),
    excel_file:    UploadFile = File(...),
):
    # ── 1. Validate and parse windows JSON ───────────────────────────────────
    try:
        windows_input: list[dict] = json.loads(windows)
        if not isinstance(windows_input, list) or len(windows_input) == 0:
            raise ValueError("windows must be a non-empty JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid windows field: {exc}")

    required_win_keys = {"start_time", "end_time", "batch_size", "interval_secs", "email_count"}
    for i, win in enumerate(windows_input):
        missing = required_win_keys - win.keys()
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Window {i+1} is missing required keys: {missing}"
            )
        if win["start_time"] >= win["end_time"]:
            raise HTTPException(
                status_code=422,
                detail=f"Window {i+1}: start_time ({win['start_time']}) must be before end_time ({win['end_time']})"
            )
        if win["batch_size"] < 1:
            raise HTTPException(status_code=422, detail=f"Window {i+1}: batch_size must be >= 1")
        if win["interval_secs"] < 10:
            raise HTTPException(status_code=422, detail=f"Window {i+1}: interval_secs must be >= 10")
        if win["email_count"] < 1:
            raise HTTPException(status_code=422, detail=f"Window {i+1}: email_count must be >= 1")

    # ── 2. Validate date format ───────────────────────────────────────────────
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"day must be in YYYY-MM-DD format, got: {day!r}")

    # ── 3. Validate file types ────────────────────────────────────────────────
    if not template_file.filename.endswith(".html"):
        raise HTTPException(status_code=422, detail="template_file must be an .html file")
    if not excel_file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=422, detail="excel_file must be an .xlsx file")

    # ── 4. Save uploaded files ────────────────────────────────────────────────
    os.makedirs("uploads", exist_ok=True)
    excel_path    = f"uploads/{excel_file.filename}"
    template_path = f"uploads/{template_file.filename}"

    try:
        excel_bytes = await excel_file.read()      # read fully into memory first
        if not excel_bytes:
            raise HTTPException(status_code=422, detail="excel_file is empty")
        with open(excel_path, "wb") as f:
            f.write(excel_bytes)

        template_bytes = await template_file.read()
        if not template_bytes:
            raise HTTPException(status_code=422, detail="template_file is empty")
        with open(template_path, "wb") as f:
            f.write(template_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {exc}")

    try:
        template_str = template_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="template_file is not valid UTF-8 text")

    # ── 5. Read and validate Excel ────────────────────────────────────────────
    try:
        users_df = read_excel(excel_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse Excel file: {exc}")

    if len(users_df) == 0:
        raise HTTPException(status_code=422, detail="Excel file has no data rows")

    missing_cols = {"email", "subject"} - set(users_df.columns)
    if missing_cols:
        raise HTTPException(
            status_code=422,
            detail=f"Excel is missing required columns: {missing_cols}. "
                   f"Found columns: {list(users_df.columns)}"
        )

    # ── 6. Validate email counts fit the data ────────────────────────────────
    total_assigned = sum(w["email_count"] for w in windows_input)
    if total_assigned > len(users_df):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Sum of email_count across all windows ({total_assigned:,}) "
                f"exceeds available Excel rows ({len(users_df):,}). "
                f"Reduce your window email counts by at least {total_assigned - len(users_df):,}."
            )
        )

    # ── 7. Build schedule in DB ───────────────────────────────────────────────
    schedule_id = uuid.uuid4().hex
    try:
        create_schedule(schedule_id, name, day, template_str, total_assigned, timezone)

        all_rows = users_df.to_dicts()
        cursor   = 0

        for win in windows_input:
            wid = add_time_window(
                schedule_id,
                win["start_time"], win["end_time"],
                win["batch_size"], win["interval_secs"], win["email_count"],
            )
            chunk     = all_rows[cursor : cursor + win["email_count"]]
            cursor   += win["email_count"]
            n_batches = math.ceil(len(chunk) / win["batch_size"])

            db_rows = []
            for batch_num in range(1, n_batches + 1):
                start = (batch_num - 1) * win["batch_size"]
                end   = start + win["batch_size"]
                for user in chunk[start:end]:
                    email   = user.pop("email", "")
                    subject = user.pop("subject", "")
                    extra   = json.dumps(user)
                    db_rows.append((schedule_id, wid, email, subject, extra, batch_num))

            bulk_insert_emails(db_rows)

    except HTTPException:
        raise
    except Exception as exc:
        # Roll back the schedule row if anything blew up mid-way
        try:
            delete_schedule(schedule_id)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to build schedule: {exc}")

    return {
        "schedule_id":   schedule_id,
        "total_emails":  total_assigned,
        "windows":       len(windows_input),
        "excel_rows":    len(users_df),
    }


@app.get("/schedules")
async def list_schedules():
    return get_all_schedules()


@app.get("/schedules/{schedule_id}")
async def get_schedule_detail(schedule_id: str):
    sched = get_schedule(schedule_id)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    windows = get_windows(schedule_id)
    return {**sched, "windows": windows}


@app.delete("/schedules/{schedule_id}")
async def delete_schedule_api(schedule_id: str):
    delete_schedule(schedule_id)
    return {"deleted": schedule_id}


@app.get("/schedules/{schedule_id}/logs")
async def get_logs(schedule_id: str):
    return get_batch_logs(schedule_id)


@app.post("/schedules/{schedule_id}/activate")
async def activate_schedule(schedule_id: str):
    update_schedule_status(schedule_id, "active")
    return {"status": "active"}


@app.post("/schedules/{schedule_id}/pause")
async def pause_schedule(schedule_id: str):
    update_schedule_status(schedule_id, "paused")
    return {"status": "paused"}


# ── SSE live stream ───────────────────────────────────────────────────────────

@app.get("/schedules/{schedule_id}/stream")
async def sse_stream(schedule_id: str):
    if not get_schedule(schedule_id):
        raise HTTPException(404, "Schedule not found")

    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    register_listener(schedule_id, q)

    async def event_gen():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "schedule_done":
                        break
                except asyncio.TimeoutError:
                    yield ": ping\n\n"   # keep-alive
        finally:
            unregister_listener(schedule_id, q)

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})