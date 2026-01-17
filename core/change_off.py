from datetime import datetime, date, time
from core.holiday import load_holidays


# =========================
# HELPER
# =========================
def calc_hours(start_time: time, end_time: time) -> float:
    start = datetime.combine(date.today(), start_time)
    end = datetime.combine(date.today(), end_time)

    if end < start:
        end = end.replace(day=end.day + 1)

    return round((end - start).seconds / 3600, 2)


def get_day_type(work_date: date, holidays: set) -> str:
    """
    Return:
    - 'weekday'
    - 'weekend'
    - 'holiday'
    """
    if work_date in holidays:
        return "holiday"

    if work_date.weekday() >= 5:
        return "weekend"

    return "weekday"


# =========================
# MAIN LOGIC
# =========================
def calculate_co(
    category: str,
    work_type: str,
    work_date: date,
    start_time: time,
    end_time: time,
    is_travelling: bool = False,   # ✅ OPTIONAL (checkbox)
    is_standby: bool = False       # ✅ OPTIONAL (checkbox)
) -> tuple[float, str]:

    holidays = load_holidays()
    day_type = get_day_type(work_date, holidays)
    hours = calc_hours(start_time, end_time)

    co = 0.0

    # =====================================================
    # 1️⃣ BASE CO (PEKERJAAN UTAMA)
    # =====================================================

    # --- TEKNISI / ENGINEER ---
    if category == "Teknisi / Engineer":

        if work_type == "3-shift":
            if day_type in ["weekend", "holiday"]:
                co = 0.5

        elif work_type == "2-shift":
            if day_type == "weekday":
                co = 0.5
            else:
                co = 1.5

        elif work_type == "non-shift":
            if day_type == "weekday":
                if hours > 12:
                    co = 1.0
            else:
                if hours <= 12:
                    co = 1.0
                else:
                    co = 2.0

    # --- BACK OFFICE / WORKSHOP ---
    elif category == "Back Office / Workshop":

        if day_type == "weekday":
            if hours > 12:
                co = 1.0
        else:
            if hours <= 12:
                co = 1.0
            else:
                co = 2.0

    # =====================================================
    # 2️⃣ BONUS CO (CHECKBOX TRAVELLING / STANDBY)
    # Berlaku HANYA weekend / holiday
    # =====================================================
    if day_type in ["weekend", "holiday"]:

        # --- STANDBY ---
        if is_standby:
            co += 0.5

        # --- TRAVELLING ---
        if is_travelling:
            if start_time < time(12, 0):
                co += 0.5
            else:
                co += 0.5

    return round(co, 2), day_type
