from core.db import get_conn
from core.auth import hash_password

def seed_hr_if_empty():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute("""
            INSERT INTO users (nik, name, email, role, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "HR001",
            "HR Admin",
            "hr@cistech.co.id",
            "hr",
            hash_password("admin123")
        ))
        conn.commit()
        print("✅ Default HR Admin created")

    conn.close()
