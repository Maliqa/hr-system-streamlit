from datetime import date
from core.db import get_conn

def is_holiday(check_date: date) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM holidays WHERE date = ?",
        (check_date.isoformat(),)
    ).fetchone()
    conn.close()
    return row is not None

