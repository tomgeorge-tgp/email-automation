"""
scheduler_service.py — APScheduler-based cron that fires batches based on time windows.
Runs inside the FastAPI process; survives frontend restarts (state lives in SQLite).
"""

import asyncio
import json
import logging
import math
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.db import (
    get_all_schedules,
    get_windows,
    get_pending_batch,
    get_last_batch_log,
    get_max_batch_number,
    log_batch,
    mark_email,
    update_schedule_status,
    update_window_status,
)
from services.email_service import send_email
from services.template_service import render_template

logger = logging.getLogger("scheduler")

_scheduler: AsyncIOScheduler | None = None

# Global broadcast queues: schedule_id -> list of asyncio.Queue (SSE listeners)
_listeners: dict[str, list[asyncio.Queue]] = {}

_send_semaphore = asyncio.Semaphore(20)


def register_listener(schedule_id: str, q: asyncio.Queue):
    _listeners.setdefault(schedule_id, []).append(q)


def unregister_listener(schedule_id: str, q: asyncio.Queue):
    if schedule_id in _listeners:
        try:
            _listeners[schedule_id].remove(q)
        except ValueError:
            pass


async def _broadcast(schedule_id: str, event: dict):
    dead = []
    for q in _listeners.get(schedule_id, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        unregister_listener(schedule_id, q)


# ── Core tick ─────────────────────────────────────────────────────────────────

async def _tick():
    """Runs every 60 s. Checks all active/pending schedules."""
    now_utc = datetime.now(ZoneInfo("UTC"))

    schedules = get_all_schedules()
    for sched in schedules:
        if sched["status"] in ("done", "error"):
            continue

        # Get current time in schedule's timezone
        tz_name = sched.get("timezone", "UTC")
        try:
            now_tz = now_utc.astimezone(ZoneInfo(tz_name))
        except Exception:
            now_tz = now_utc # fallback

        today_str = now_tz.strftime("%Y-%m-%d")
        now_time  = now_tz.strftime("%H:%M")

        if sched["day"] != today_str:
            continue

        windows = get_windows(sched["id"])
        all_done = True

        for win in windows:
            if win["status"] == "done":
                continue
            all_done = False

            # Is now inside this window?
            if not (win["start_time"] <= now_time <= win["end_time"]):
                continue

            update_schedule_status(sched["id"], "active")

            last_log = get_last_batch_log(win["id"])
            max_batch = get_max_batch_number(win["id"])

            if last_log:
                # Respect interval (with ±20% jitter)
                jitter = random.uniform(0.8, 1.2)
                next_at_str = last_log["next_batch_at"]
                if next_at_str:
                    next_at = datetime.fromisoformat(next_at_str)
                    if now_tz < next_at:
                        continue
                next_batch = last_log["batch_number"] + 1
            else:
                next_batch = 1

            if next_batch > max_batch:
                update_window_status(win["id"], "done")
                logger.info("Window %s done", win["id"])
                continue

            emails = get_pending_batch(win["id"], next_batch)
            if not emails:
                update_window_status(win["id"], "done")
                continue

            template_str = sched["template_str"]
            sent = failed = 0

            async def send_one(em):
                async with _send_semaphore:
                    try:
                        extra = json.loads(em["extra_data"])
                        extra["email"]   = em["recipient_email"]
                        extra["subject"] = em["subject"]
                        html_body = render_template(template_str, extra)
                        await send_email(em["recipient_email"], em["subject"], html_body)
                        mark_email(em["id"], "sent")
                        await _broadcast(sched["id"], {
                            "type": "progress",
                            "email": em["recipient_email"],
                            "status": "sent",
                            "batch": next_batch,
                            "window": f"{win['start_time']}–{win['end_time']}",
                        })
                        return True
                    except Exception as exc:
                        mark_email(em["id"], "failed", str(exc))
                        await _broadcast(sched["id"], {
                            "type": "progress",
                            "email": em["recipient_email"],
                            "status": "failed",
                            "error": str(exc),
                            "batch": next_batch,
                            "window": f"{win['start_time']}–{win['end_time']}",
                        })
                        return False

            tasks = [send_one(em) for em in emails]
            results = await asyncio.gather(*tasks)
            sent = sum(1 for r in results if r)
            failed = len(results) - sent

            jitter_secs = int(win["interval_secs"] * random.uniform(0.8, 1.2))
            next_at = (now_tz + timedelta(seconds=jitter_secs)).isoformat()
            log_batch(sched["id"], win["id"], next_batch, sent, failed, next_at)

            logger.info(
                "Schedule %s | window %s–%s | batch %d/%d | sent=%d failed=%d",
                sched["id"], win["start_time"], win["end_time"],
                next_batch, max_batch, sent, failed,
            )

            await _broadcast(sched["id"], {
                "type": "batch_done",
                "batch": next_batch,
                "max_batch": max_batch,
                "sent": sent,
                "failed": failed,
                "next_at": next_at,
            })

        if all_done:
            update_schedule_status(sched["id"], "done")
            await _broadcast(sched["id"], {"type": "schedule_done"})


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(_tick, "interval", seconds=60, id="main_tick", replace_existing=True)
    _scheduler.start()
    logger.info("Scheduler started — ticking every 60 s")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)