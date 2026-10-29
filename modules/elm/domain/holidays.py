# Static holiday list for tests (YYYYMMDD format)
import datetime

# Example holidays - can be extended later
def get_holidays(year: int) -> list[datetime.date]:
    return [
        datetime.date(year, 1, 1),   # New Year's Day
        datetime.date(year, 8, 15),  # Independence Day (India)
        datetime.date(year, 10, 2),  # Gandhi Jayanti
    ]
