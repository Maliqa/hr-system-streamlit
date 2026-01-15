from datetime import datetime, date, time
from core.holiday import load_holidays



# =========================
# HELPER
# =========================
def is_holiday_or_weekend(d: date, holidays: set) -> bool:
    return d.weekday() >= 5 or d in holidays


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

    if work_date.weekday() >= 5:  # Saturday / Sunday
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
    end_time: time
) -> tuple[float, str]:

    holidays = load_holidays()
    day_type = get_day_type(work_date, holidays)
    hours = calc_hours(start_time, end_time)

    co = 0.0

    # =====================================================
    # 1️⃣ TRAVELLING
    # =====================================================
    if work_type == "travelling":
        if day_type == "weekday":
            co = 0
        else:  # weekend / holiday
            if start_time < time(12, 0):
                co = 1.0
            else:
                co = 0.5

    # =====================================================
    # 2️⃣ STANDBY (LUAR KOTA)
    # =====================================================
    elif work_type == "standby":
        if day_type in ["weekend", "holiday"]:
            co = 0.5
        else:
            co = 0

    # =====================================================
    # 3️⃣ TEKNISI / ENGINEER — PROJECT
    # =====================================================
    elif category == "Teknisi / Engineer":

        # --- 3 SHIFT ---
        if work_type == "3-shift":
            if day_type in ["weekend", "holiday"]:
                co = 0.5

        # --- 2 SHIFT ---
        elif work_type == "2-shift":
            if day_type == "weekday":
                co = 0.5
            else:
                co = 1.5

        # --- NON SHIFT ---
        elif work_type == "non-shift":
            if day_type == "weekday":
                if hours > 12:
                    co = 1.0
            else:
                if hours <= 12:
                    co = 1.0
                else:
                    co = 2.0

    # =====================================================
    # 4️⃣ BACK OFFICE / WORKSHOP (NON PROJECT)
    # =====================================================
    elif category == "Back Office / Workshop":

        if day_type == "weekday":
            if hours > 12:
                co = 1.0
        else:
            if hours <= 12:
                co = 1.0
            else:
                co = 2.0

    return round(co, 2), day_type
