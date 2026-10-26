"""Seed default ELM baseline leave categories and sample holiday calendar."""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.leave.models import HolidayCalendar, LeaveType


class Command(BaseCommand):
    help = "Seed baseline leave categories and sample calendar for ELM."

    def handle(self, *args, **options):
        types = [
            {
                "code": "CL",
                "name": "Casual Leave",
                "max_days_per_year": Decimal("8.0"),
                "requires_substitute": True,
                "is_continuous_counting": False,
                "can_carry_forward": False,
                "description": "8 days/year; half-day allowed; lapses at year-end.",
            },
            {
                "code": "RH",
                "name": "Restricted Holiday",
                "max_days_per_year": Decimal("2.0"),
                "requires_substitute": True,
                "is_continuous_counting": False,
                "can_carry_forward": False,
                "description": "2 days/year; must match published RH list.",
            },
            {
                "code": "SCL",
                "name": "Special Casual Leave",
                "max_days_per_year": Decimal("15.0"),
                "requires_substitute": True,
                "is_continuous_counting": False,
                "can_carry_forward": False,
                "description": "Up to 15 days/year for admissible official purpose.",
            },
            {
                "code": "EL",
                "name": "Earned Leave",
                "max_days_per_year": Decimal("30.0"),
                "requires_substitute": True,
                "is_continuous_counting": True,
                "can_carry_forward": True,
                "description": "Continuous counting; unused balance carries forward.",
            },
            {
                "code": "COL",
                "name": "Commuted Leave",
                "max_days_per_year": Decimal("20.0"),
                "requires_substitute": True,
                "is_continuous_counting": True,
                "can_carry_forward": True,
                "description": "Medical basis; continuous counting; carries forward.",
            },
            {
                "code": "VL",
                "name": "Vacation Leave",
                "max_days_per_year": Decimal("60.0"),
                "requires_substitute": True,
                "is_continuous_counting": True,
                "can_carry_forward": False,
                "description": "Faculty vacation periods; converts to EL at year-end.",
            },
        ]

        for item in types:
            LeaveType.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "max_days_per_year": item["max_days_per_year"],
                    "requires_substitute": item["requires_substitute"],
                    "is_continuous_counting": item["is_continuous_counting"],
                    "can_carry_forward": item["can_carry_forward"],
                    "is_active": True,
                    "description": item["description"],
                },
            )
            self.stdout.write(f"  seeded leave type {item['code']}")

        holidays = [
            ("Republic Day", date(2026, 1, 26), False, 2026),
            ("Holi", date(2026, 3, 25), False, 2026),
            ("Good Friday", date(2026, 4, 3), False, 2026),
            ("Independence Day", date(2026, 8, 15), False, 2026),
            ("Mahatma Gandhi Jayanti", date(2026, 10, 2), False, 2026),
            ("Dussehra", date(2026, 10, 20), False, 2026),
            ("Diwali", date(2026, 11, 8), False, 2026),
            ("Guru Nanak Jayanti", date(2026, 11, 24), False, 2026),
            ("Christmas", date(2026, 12, 25), False, 2026),
            ("Maha Shivratri", date(2026, 2, 17), True, 2026),
            ("Raksha Bandhan", date(2026, 8, 28), True, 2026),
            ("Govardhan Puja", date(2026, 11, 9), True, 2026),
            ("Bhai Dooj", date(2026, 11, 10), True, 2026),
        ]

        for name, d, is_rh, yr in holidays:
            HolidayCalendar.objects.update_or_create(
                date=d,
                name=name,
                defaults={"is_restricted": is_rh, "year": yr},
            )
            kind = "RH" if is_rh else "Holiday"
            self.stdout.write(f"  seeded {kind}: {name} ({d})")
