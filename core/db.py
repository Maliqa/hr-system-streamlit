import sqlite3
import os

DB_PATH = "data/hr.db"

def get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nik TEXT UNIQUE,
        name TEXT,
        email TEXT UNIQUE,
        role TEXT,
        join_date DATE,
        probation_date DATE,
        permanent_date DATE,
        password_hash TEXT,
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
        updated_at DATE
    )
    """)

    conn.commit()
    conn.close()
