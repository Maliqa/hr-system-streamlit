from datetime import time as dtime

# ======================================================
# CHANGE OFF CALCULATION (SINGLE SOURCE OF TRUTH)
# ======================================================
def calculate_co(work_type, work_date, end_time, hours):
    """
    Calculate Change Off (CO) value based on work type and conditions.
    Returns float (days).
    """
    is_holiday = work_date.weekday() >= 5  # Saturday / Sunday

    if work_type == "travelling":
        if not is_holiday or end_time is None:
            return 0.0
        return 1.0 if end_time < dtime(12, 0) else 0.5

    if work_type == "standby":
        return 0.5 if is_holiday else 0.0

    if work_type == "3-shift":
        return 1.0 if is_holiday else 0.0

    if work_type == "2-shift":
        return 1.5 if is_holiday else 0.5

    if work_type in ["non-shift", "back-office"]:
        if hours is None:
            return 0.0
        if is_holiday:
            return 2.0 if hours >= 12 else 1.0
        return 1.0 if hours >= 12 else 0.0

    return 0.0
