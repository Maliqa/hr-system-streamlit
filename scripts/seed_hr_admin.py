from core.db import get_conn
from core.auth import hash_password
from datetime import date

conn = get_conn()
cur = conn.cursor()

email = "hr@cistech.co.id"
password = "admin123"

cur.execute("""
INSERT INTO users (nik, name, email, role, join_date, permanent_date, password_hash)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    "HR001",
    "HR Admin",
    email,
    "hr",
    date.today().isoformat(),
    date.today().isoformat(),
    hash_password(password)
))

user_id = cur.lastrowid

cur.execute("""
INSERT INTO leave_balance (user_id, last_year, current_year, change_off, sick_no_doc)
VALUES (?, 0, 0, 0, 0)
""", (user_id,))

conn.commit()
conn.close()

print("✅ HR Admin created")
print("📧 Email:", email)
print("🔑 Password:", password)
