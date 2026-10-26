"""Demo leave policies and faculty balances.

The ELM module needs two pieces of reference data before an employee can use
it: a policy per leave category (the entitlement) and a balance row for the
year. Without them the Apply screen fails closed with "No policy" even for a
correctly authenticated faculty member.

    manage.py seed_leave_demo

Idempotent. The entitlement numbers here are demo values — the establishment
replaces them through the Leave Policy screen; re-running this command never
overwrites an existing policy row or balance.
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.directory.models import UserRef
from modules.leave.models import (
    EmployeeType,
    LeaveCategory,
    LeavePolicy,
)
from modules.leave.services.balances import ensure_user_balances

#: (category, annual entitlement, carries forward, half day allowed)
FACULTY_POLICIES = (
    (LeaveCategory.CL, "12.00", False, True),
    (LeaveCategory.RH, "2.00", False, False),
    (LeaveCategory.SCL, "10.00", False, False),
    (LeaveCategory.EL, "15.00", True, False),
    (LeaveCategory.VL, "30.00", True, False),
)

NON_FACULTY_POLICIES = (
    (LeaveCategory.CL, "8.00", False, True),
    (LeaveCategory.RH, "2.00", False, False),
    (LeaveCategory.SCL, "10.00", False, False),
    (LeaveCategory.EL, "15.00", True, False),
    (LeaveCategory.COL, "15.00", True, False),
)


class Command(BaseCommand):
    help = "Seed demo leave policies and balances for every faculty member"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=None,
            help="Leave year to provision (default: current year).")
        parser.add_argument(
            "--user-id", type=int, action="append", default=[],
            help="Extra user id to provision, e.g. a test account. Repeatable.")

    @transaction.atomic
    def handle(self, *args, **opts):
        year = opts["year"] or date.today().year
        effective_from = date(year, 1, 1)

        for employee_type, policies in (
            (EmployeeType.FACULTY, FACULTY_POLICIES),
            (EmployeeType.NON_FACULTY, NON_FACULTY_POLICIES),
        ):
            for category, entitlement, carries, half_day in policies:
                LeavePolicy.objects.get_or_create(
                    category=category,
                    employee_type=employee_type,
                    effective_from=effective_from,
                    defaults={
                        "annual_entitlement": Decimal(entitlement),
                        "carries_forward": carries,
                        "half_day_allowed": half_day,
                        "is_active": True,
                    },
                )
        self.stdout.write(f"  policies ready for {year}")

        user_ids = set(opts["user_id"])
        user_ids.update(
            UserRef.objects.filter(kind="faculty", is_active=True)
            .values_list("user_id", flat=True))
        try:
            from fusion_auth.client import get_client

            user_ids.update(
                u.user_id for u in get_client().search_users(kind="faculty", limit=100))
        except Exception as exc:                              # noqa: BLE001
            self.stdout.write(self.style.WARNING(
                f"  IAM not reachable ({exc}); using local directory only"))

        for user_id in sorted(user_ids):
            ensure_user_balances(user_id, EmployeeType.FACULTY, year)

        self.stdout.write(self.style.SUCCESS(
            f"  {len(user_ids)} faculty balance set(s) for {year}"))
