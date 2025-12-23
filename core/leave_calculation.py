from datetime import date, timedelta
from core.db import get_conn


def get_holiday_dates():
    """
    Ambil semua tanggal libur dari database.
    Return dalam bentuk set of string: {'2025-12-25', ...}
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT holiday_date FROM holidays"
    ).fetchall()
    conn.close()

    return set(row[0] for row in rows)


def calculate_leave_days(start_date: date, end_date: date) -> int:
    """
    Hitung jumlah hari cuti valid:
    - Senin–Jumat
    - BUKAN hari libur
    """
    holidays = get_holiday_dates()

    total_days = 0
    current = start_date

    while current <= end_date:
        is_weekday = current.weekday() < 5      # Senin–Jumat
        is_holiday = current.isoformat() in holidays

        if is_weekday and not is_holiday:
            total_days += 1

        current += timedelta(days=1)

    return total_days
