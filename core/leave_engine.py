from datetime import date
from core.leave_accrual import run_monthly_accrual
from core.leave_reset import run_june_30_reset

def run_leave_engine(today: date | None = None):
    if not today:
        today = date.today()

    # 1️⃣ Monthly accrual (+1 setiap tanggal 1)
    run_monthly_accrual(today)

    # 2️⃣ Annual reset (30 Juni)
    run_june_30_reset(today)
