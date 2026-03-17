
import asyncio
import os
import shutil
import uuid

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from services.excel_service import read_excel
from services.batch_sender import send_bulk_emails

app = FastAPI()

os.makedirs("uploads", exist_ok=True)

# In-memory job store: job_id -> { queue, status, total, success, failed }
jobs: dict[str, dict] = {}


@app.post("/send-bulk-emails")
async def send_bulk_emails_api(
    template_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
):
    template_path = f"uploads/{template_file.filename}"
    excel_path = f"uploads/{excel_file.filename}"

    with open(template_path, "wb") as f:
        shutil.copyfileobj(template_file.file, f)
    with open(excel_path, "wb") as f:
        shutil.copyfileobj(excel_file.file, f)

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    users_df = read_excel(excel_path)

    if len(users_df) == 0:
        return {"job_id": None, "total": 0, "message": "No users found in Excel file."}

    job_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    jobs[job_id] = {
        "queue": queue,
        "status": "running",
        "total": len(users_df),
        "success": 0,
        "failed": 0,
    }

    # Fire background task — POST returns immediately with job_id
    asyncio.create_task(_run_job(job_id, template_str, users_df, queue))

    return {"job_id": job_id, "total": len(users_df)}


async def _run_job(job_id: str, template_str: str, users_df, queue: asyncio.Queue):
    job = jobs[job_id]
    try:
        await send_bulk_emails(
            template_str=template_str,
            users_df=users_df,
            concurrency=10,
            batch_size=50,
            queue=queue,
        )
        job["status"] = "complete"
    except Exception:
        job["status"] = "error"
        # batch_sender already put an error event on the queue


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
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
