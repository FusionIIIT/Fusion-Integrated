"""Seed the pilot leave types, effective from a date.

Idempotent: a type that already has a version effective that day is left alone.
The entitlements here are pilot defaults; the institute's own figures come from
the spec and are recorded by creating a new version, never by editing these.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.elm.models import LeaveType

#: code, name, entitlement, counts calendar days, half day, reason required.
DEFAULT_TYPES = [
    ("CL", "Casual Leave", "8.0", False, True, False),
    ("EL", "Earned Leave", "15.0", False, False, False),
    ("VL", "Vacation Leave", "15.0", False, False, False),
    ("COL", "Compensatory Off", "0.0", False, False, True),
    ("RH", "Restricted Holiday", "2.0", False, False, False),
]


class Command(BaseCommand):
    help = "Seed the leave types (effective today unless overridden)"

    def add_arguments(self, parser):
        parser.add_argument("--effective-from", default=None,
                            help="YYYY-MM-DD; defaults to today")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["effective_from"]:
            effective = date.fromisoformat(options["effective_from"])
        else:
            effective = timezone.localdate()

        created = 0
        for code, name, entitlement, calendar_days, half_day, reason in DEFAULT_TYPES:
            _, made = LeaveType.objects.get_or_create(
                code=code, effective_from=effective,
                defaults={"name": name,
                          "annual_entitlement_days": entitlement,
                          "counts_calendar_days": calendar_days,
                          "allows_half_day": half_day,
                          "requires_reason": reason})
            created += int(made)
            self.stdout.write(f"  {'created' if made else 'present'}: {code} {name}")
        self.stdout.write(self.style.SUCCESS(
            f"{created} leave type version(s) created effective {effective}"))
