from django.db.models import Q

from modules.leave.models import HolidayCalendar, VacationPeriod

def get_published_calendar(year: int):
    """
    Returns the published holiday calendar for a given year.
    
    :param year: The year to filter the calendar by.
    :return: A queryset of HolidayCalendar objects that are published and match the year.
    """
    return HolidayCalendar.objects.filter(year=year, is_published=True).order_by('date')

def get_vacation_periods(year: int):
    """
    Returns the active vacation periods for a given year.
    
    :param year: The year to filter the vacation periods by.
    :return: A queryset of VacationPeriod objects that are active and match the year.
    """
    return VacationPeriod.objects.filter(year=year, is_active=True).order_by('start_date')