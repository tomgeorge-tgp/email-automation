"""
db.py — SQLite persistence for schedules, email queue, and batch logs.
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path("email_scheduler.db")

_local = threading.local()


@contextmanager
def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield _local.conn
        _local.conn.commit()
    except Exception:
        _local.conn.rollback()
        raise


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schedules (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            day             TEXT NOT NULL,           -- YYYY-MM-DD
            template_str    TEXT NOT NULL,
            total_emails    INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'pending',  -- pending/active/paused/done/error
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS time_windows (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id     TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
            start_time      TEXT NOT NULL,   -- HH:MM  (24h)
            end_time        TEXT NOT NULL,
            batch_size      INTEGER NOT NULL DEFAULT 70,
            interval_secs   INTEGER NOT NULL DEFAULT 120,
            email_count     INTEGER NOT NULL DEFAULT 0,
            batches_sent    INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'pending'   -- pending/active/done
        );

        CREATE TABLE IF NOT EXISTS email_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id     TEXT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
            window_id       INTEGER NOT NULL REFERENCES time_windows(id) ON DELETE CASCADE,
            recipient_email TEXT NOT NULL,
            subject         TEXT NOT NULL,
            extra_data      TEXT NOT NULL DEFAULT '{}',   -- JSON
            batch_number    INTEGER NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'pending',  -- pending/sent/failed/retrying
            error_msg       TEXT,
            sent_at         TEXT,
            retry_count     INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS batch_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id     TEXT NOT NULL,
            window_id       INTEGER NOT NULL,
            batch_number    INTEGER NOT NULL,
            emails_sent     INTEGER NOT NULL DEFAULT 0,
            emails_failed   INTEGER NOT NULL DEFAULT 0,
            executed_at     TEXT NOT NULL,
            next_batch_at   TEXT
        );
        """)


# ── Schedule CRUD ─────────────────────────────────────────────────────────────

def create_schedule(schedule_id: str, name: str, day: str, template_str: str, total_emails: int):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO schedules (id, name, day, template_str, total_emails, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (schedule_id, name, day, template_str, total_emails, now, now),
        )


def add_time_window(schedule_id: str, start_time: str, end_time: str,
                     batch_size: int, interval_secs: int, email_count: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO time_windows (schedule_id, start_time, end_time, batch_size, interval_secs, email_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (schedule_id, start_time, end_time, batch_size, interval_secs, email_count),
        )
        return cur.lastrowid


def bulk_insert_emails(rows: list[tuple]):
    """rows: list of (schedule_id, window_id, email, subject, extra_json, batch_number)"""
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO email_queue (schedule_id, window_id, recipient_email, subject, extra_data, batch_number) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )


def get_all_schedules() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT s.*, "
            "  (SELECT COUNT(*) FROM email_queue WHERE schedule_id=s.id AND status='sent') as sent_count, "
            "  (SELECT COUNT(*) FROM email_queue WHERE schedule_id=s.id AND status='failed') as failed_count, "
            "  (SELECT COUNT(*) FROM email_queue WHERE schedule_id=s.id AND status='pending') as pending_count "
            "FROM schedules s ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_schedule(schedule_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,)).fetchone()
        return dict(row) if row else None


def get_windows(schedule_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM time_windows WHERE schedule_id=? ORDER BY start_time", (schedule_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_pending_batch(window_id: int, batch_number: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM email_queue WHERE window_id=? AND batch_number=? AND status IN ('pending','retrying')",
            (window_id, batch_number),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_email(email_id: int, status: str, error: str | None = None):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE email_queue SET status=?, error_msg=?, sent_at=? WHERE id=?",
            (status, error, now if status == "sent" else None, email_id),
        )


def log_batch(schedule_id: str, window_id: int, batch_number: int,
              sent: int, failed: int, next_at: str | None):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO batch_log (schedule_id, window_id, batch_number, emails_sent, emails_failed, executed_at, next_batch_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (schedule_id, window_id, batch_number, sent, failed, now, next_at),
        )
        conn.execute(
            "UPDATE time_windows SET batches_sent=batches_sent+1 WHERE id=?", (window_id,)
        )


def update_schedule_status(schedule_id: str, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE schedules SET status=?, updated_at=? WHERE id=?",
            (status, datetime.now().isoformat(), schedule_id),
        )


def update_window_status(window_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE time_windows SET status=? WHERE id=?", (status, window_id))


def get_last_batch_log(window_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM batch_log WHERE window_id=? ORDER BY executed_at DESC LIMIT 1",
            (window_id,),
        ).fetchone()
        return dict(row) if row else None


def get_max_batch_number(window_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(batch_number) as mx FROM email_queue WHERE window_id=?", (window_id,)
        ).fetchone()
        return row["mx"] or 0


def delete_schedule(schedule_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))


def get_batch_logs(schedule_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT bl.*, tw.start_time, tw.end_time FROM batch_log bl "
            "JOIN time_windows tw ON tw.id=bl.window_id "
            "WHERE bl.schedule_id=? ORDER BY bl.executed_at DESC LIMIT 100",
            (schedule_id,),
        ).fetchall()
        return [dict(r) for r in rows]