from datetime import date
from core.db import get_conn

def run_june_30_reset(today: date | None = None, executed_by: int | None = None):
    if not today:
        today = date.today()

    # Hanya boleh jalan 30 Juni
    if today.month != 6 or today.day != 30:
        return False, "Not June 30th"

    year = today.year

    conn = get_conn()
    cur = conn.cursor()

    # Cegah double reset di tahun yang sama
    already = cur.execute("""
        SELECT 1 FROM leave_reset_logs WHERE year=?
    """, (year,)).fetchone()

    if already:
        conn.close()
        return False, "June 30 reset already executed"

    # RESET LOGIC (FINAL)
    cur.execute("""
        UPDATE leave_balance
        SET last_year = current_year,
            current_year = 0,
            updated_at = DATE('now')
    """)

    # LOG RESET
    cur.execute("""
        INSERT INTO leave_reset_logs (year, executed_by)
        VALUES (?, ?)
    """, (year, executed_by))

    conn.commit()
    conn.close()

    return True, "June 30 leave reset completed"
