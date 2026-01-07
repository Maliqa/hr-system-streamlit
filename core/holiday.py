from datetime import date, timedelta
from core.db import get_conn


def load_holidays():
    conn = get_conn()
    rows = conn.execute("""
        SELECT holiday_date FROM holidays
    """).fetchall()

    holidays = set()
    for r in rows:
        try:
            holidays.add(date.fromisoformat(str(r[0])[:10]))
        except:
            pass

    return holidays


def is_workday(d: date, holidays: set) -> bool:
    if d.weekday() >= 5:  # Saturday / Sunday
        return False
    if d in holidays:
        return False
    return True


def calculate_working_days(start: date, end: date) -> int:
    holidays = load_holidays()
    days = 0
    d = start
    while d <= end:
        if is_workday(d, holidays):
            days += 1
        d += timedelta(days=1)
    return days
