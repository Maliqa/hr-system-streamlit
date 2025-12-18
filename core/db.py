import sqlite3
import os

DB_PATH = "data/hr.db"


# =========================
# CONNECTION
# =========================
def get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# =========================
# INIT DATABASE
# =========================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # =========================
    # USERS
    # =========================
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

    # =========================
    # LEAVE BALANCE
    # =========================
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

    # =========================
    # LEAVE REQUESTS (🔥 WAJIB)
    # =========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        leave_type TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        total_days INTEGER NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_by INTEGER,
        approved_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (approved_by) REFERENCES users(id)
    )
    """)

    # =========================
    # HOLIDAYS (untuk validasi cuti)
    # =========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holiday_date DATE UNIQUE,
        description TEXT
    )
    """)

    # =========================
    # CHANGE OFF CLAIMS (NEXT)
    # =========================
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
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_by INTEGER,
        approved_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()
