import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("email_scheduler.db")

def check():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    print("--- Batch Log ---")
    rows = conn.execute("SELECT * FROM batch_log").fetchall()
    for r in rows:
        print(dict(r))
        
    conn.close()

if __name__ == "__main__":
    check()
