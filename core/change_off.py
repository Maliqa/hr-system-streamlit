from datetime import datetime, date, time
from core.holiday import load_holidays


def get_day_type(work_date: date, holidays: set) -> str:
    if work_date in holidays:
        return "holiday"
    if work_date.weekday() >= 5:
        return "weekend"
    return "weekday"


def calc_hours(start_time: time, end_time: time) -> float:
    start = datetime.combine(date.today(), start_time)
    end = datetime.combine(date.today(), end_time)
    if end < start:
        end = end.replace(day=end.day + 1)
    return round((end - start).seconds / 3600, 2)


def calculate_co(
    category: str,
    work_type: str,
    work_date: date,
    start_time: time,
    end_time: time,
    travelling: bool = False,
    standby: bool = False
) -> tuple[float, str, float]:

    holidays = load_holidays()
    day_type = get_day_type(work_date, holidays)
    hours = calc_hours(start_time, end_time)

    co = 0.0

    # =====================================================
    # BASE WORK TYPE
    # =====================================================
    if work_type == "3-shift":
        if day_type in ["weekend", "holiday"]:
            co += 1.0

    elif work_type == "2-shift":
        if day_type == "weekday":
            co += 0.5
        else:
            co += 1.5

    elif work_type == "non-shift":
        if day_type == "weekday":
            if hours > 12:
                co += 1.0
        else:
            if hours <= 12:
                co += 1.0
            else:
                co += 2.0

    elif work_type == "back-office":
        if day_type == "weekday":
            if hours > 12:
                co += 1.0
        else:
            if hours <= 12:
                co += 1.0
            else:
                co += 2.0

    # =====================================================
    # ADDITIONAL ACTIVITY
    # =====================================================
    if travelling and day_type in ["weekend", "holiday"]:
        if work_type in ["2-shift", "3-shift"]:
            if start_time < time(12, 0):
                co += 1.0
            else:
                co += 0.5
        else:
            co += 0.5

    if standby and day_type in ["weekend", "holiday"]:
        co += 0.5

    return round(co, 2), day_type, hours
