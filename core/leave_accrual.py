from datetime import date
from core.db import get_conn

def run_monthly_accrual(today: date | None = None):
    if not today:
        today = date.today()

    year = today.year
    month = today.month

    conn = get_conn()
    cur = conn.cursor()

    # Ambil employee yang sudah permanent
    users = cur.execute("""
        SELECT id
        FROM users
        WHERE role = 'employee'
        AND permanent_date IS NOT NULL
        AND date(permanent_date) <= date(?)
    """, (today.isoformat(),)).fetchall()

    for (user_id,) in users:
        # Cek apakah sudah accrual bulan ini
        exists = cur.execute("""
            SELECT 1 FROM accrual_logs
            WHERE user_id=? AND year=? AND month=?
        """, (user_id, year, month)).fetchone()

        if exists:
            continue  # aman, skip

        # Tambah +1 ke current_year
        cur.execute("""
            UPDATE leave_balance
            SET current_year = current_year + 1,
                updated_at = DATE('now')
            WHERE user_id=?
        """, (user_id,))

        # Log accrual
        cur.execute("""
            INSERT INTO accrual_logs (user_id, year, month, accrual_days)
            VALUES (?, ?, ?, 1)
        """, (user_id, year, month))

    conn.commit()
    conn.close()
