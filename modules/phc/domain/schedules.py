from datetime import time


def weekly_range(day_of_week: int, starts_at: time, ends_at: time) -> tuple[int, int]:
    if day_of_week not in range(7):
        raise ValueError("Choose a valid day of the week.")
    if any(value.second or value.microsecond for value in (starts_at, ends_at)):
        raise ValueError("Use whole-minute times for doctor schedule slots.")
    start = day_of_week * 1440 + starts_at.hour * 60 + starts_at.minute
    end = day_of_week * 1440 + ends_at.hour * 60 + ends_at.minute
    if end <= start:
        raise ValueError("The schedule end time must be after its start time on the same day.")
    return start, end
