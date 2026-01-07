import sqlite3
import os
# =========================
# ABSOLUTE PROJECT ROOT
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hr.db")

# =========================
# CONNECTION
# =========================
def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)
# =========================
# INIT DATABASE
# =========================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nik TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL,
        join_date DATE,
        probation_date DATE,
        permanent_date DATE,
        password_hash TEXT NOT NULL,
        manager_id INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS leave_balance (
        user_id INTEGER PRIMARY KEY,
        last_year INTEGER DEFAULT 0,
        current_year INTEGER DEFAULT 0,
        change_off REAL DEFAULT 0,
        sick_no_doc INTEGER DEFAULT 0,
        updated_at DATE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        leave_type TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        total_days INTEGER NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'submitted',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_by INTEGER,
        approved_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (approved_by) REFERENCES users(id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holiday_date DATE UNIQUE,
        description TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS change_off_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        start_date DATE,
        end_date DATE,
        location TEXT,
        daily_hours REAL,
        attachment TEXT,
        status TEXT DEFAULT 'submitted',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_by INTEGER,
        approved_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()
