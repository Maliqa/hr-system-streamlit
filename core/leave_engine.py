from datetime import date
from core.db import get_conn

def run_leave_engine():
    today = date.today()
    conn = get_conn()
    cur = conn.cursor()

    # =========================
    # JOB A: MONTHLY ACCRUAL
    # =========================
    if today.day == 1:
        last_run = cur.execute(
            "SELECT last_run FROM system_jobs WHERE job_name='monthly_leave_accrual'"
        ).fetchone()

        if not last_run or last_run[0] != today.isoformat():
            cur.execute("""
                UPDATE leave_balance
                SET current_year = current_year + 1
                WHERE user_id IN (
                    SELECT id FROM users
                    WHERE permanent_date IS NOT NULL
                    AND join_date <= DATE('now', '-1 month')
                )
            """)

            cur.execute("""
                INSERT OR REPLACE INTO system_jobs (job_name, last_run)
                VALUES ('monthly_leave_accrual', ?)
            """, (today.isoformat(),))

    # =========================
    # JOB B: LAST YEAR EXPIRY
    # =========================
    if today.month == 7 and today.day == 1:
        last_run = cur.execute(
            "SELECT last_run FROM system_jobs WHERE job_name='last_year_expiry'"
        ).fetchone()

        if not last_run or last_run[0] != today.isoformat():
            cur.execute("UPDATE leave_balance SET last_year = 0")

            cur.execute("""
                INSERT OR REPLACE INTO system_jobs (job_name, last_run)
                VALUES ('last_year_expiry', ?)
            """, (today.isoformat(),))

    # =========================
    # JOB C: YEARLY ROLLOVER
    # =========================
    if today.month == 12 and today.day == 31:
        last_run = cur.execute(
            "SELECT last_run FROM system_jobs WHERE job_name='yearly_leave_rollover'"
        ).fetchone()

        if not last_run or last_run[0] != today.isoformat():
            cur.execute("""
                UPDATE leave_balance
                SET last_year = current_year,
                    current_year = 0
            """)

            cur.execute("""
                INSERT OR REPLACE INTO system_jobs (job_name, last_run)
                VALUES ('yearly_leave_rollover', ?)
            """, (today.isoformat(),))

    conn.commit()
    conn.close()
