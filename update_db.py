import sqlite3
from pathlib import Path

DB_PATH = Path("email_scheduler.db")

def update():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("UPDATE schedules SET timezone = 'Asia/Kolkata' WHERE id = 'f32c76691eb14184a6642748701b77e5'")
    conn.commit()
    conn.close()
    print("Updated timezone for schedule f32c76691eb14184a6642748701b77e5 to Asia/Kolkata")

if __name__ == "__main__":
    update()
