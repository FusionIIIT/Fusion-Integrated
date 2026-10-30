from datetime import date
from modules.elm.models import AcademicVacationPeriod, HolidayCalendar


def get_published_holidays(year: int | None = None):
    target_year = year or date.today().year
    return HolidayCalendar.objects.filter(year=target_year, is_published=True)


def get_vacation_periods():
    return AcademicVacationPeriod.objects.all()
