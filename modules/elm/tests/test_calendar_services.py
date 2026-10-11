from datetime import date

from django.test import TestCase

from modules.elm.models import LeaveCalendar, LeaveCalendarDate
from modules.elm.services import _calendar_dates


class PublishedLeaveCalendarTests(TestCase):
    def test_dates_are_combined_from_multiple_published_years(self):
        calendar_2025 = LeaveCalendar.objects.create(
            name="Calendar 2025", year=2025, status="published",
            created_by_user_id=1, published_by_user_id=1,
        )
        calendar_2026 = LeaveCalendar.objects.create(
            name="Calendar 2026", year=2026, status="published",
            created_by_user_id=1, published_by_user_id=1,
        )
        LeaveCalendarDate.objects.create(
            calendar=calendar_2025, day=date(2025, 12, 31), name="Year-end closure",
            is_closed_day=True,
        )
        LeaveCalendarDate.objects.create(
            calendar=calendar_2026, day=date(2026, 1, 1), name="New Year closure",
            is_closed_day=True,
        )

        closed, restricted = _calendar_dates(date(2025, 12, 31), date(2026, 1, 2))

        self.assertEqual(closed, {date(2025, 12, 31), date(2026, 1, 1)})
        self.assertEqual(restricted, set())
