"""Put the specification's own figures in force so a fresh install works."""
from contextlib import suppress
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.models import AuthorityRule, HolidayCalendar, LeavePolicy
from modules.leave.services import administration

D = Decimal

# BR-EL-002, BR-EL-003, BR-EL-004, BR-EL-005, BR-EL-006, BR-EL-007, BR-EL-009
ENTITLEMENTS = [
    (Category.CL, D(8), False, None, None),
    (Category.RH, D(2), False, None, None),
    (Category.SCL, D(15), False, None, None),
    (Category.EL, D(30), True, D(300), False),
    (Category.EL, D(0), True, D(300), True),
    (Category.COL, D(20), True, D(240), None),
    (Category.VL, D(60), False, None, True),
]

# BR-EL-016 to BR-EL-019. CL and RH end with the unit head; the rest escalate.
UNIT_HEAD_FINAL = (Category.CL, Category.RH)


class Command(BaseCommand):
    help = "Seed and publish an initial leave policy, calendar and routing."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=date.today().year)
        parser.add_argument("--policy-version", default="",
                            help="Defaults to <year>.1.")
        parser.add_argument(
            "--sanctioning-designation", default="Registrar",
            help="Who finally sanctions the categories that escalate.")
        parser.add_argument(
            "--draft-only", action="store_true",
            help="Write the version but do not publish it.")

    @transaction.atomic
    def handle(self, *args, **opts) -> None:
        year = opts["year"]
        version = opts["policy_version"] or f"{year}.1"

        if LeavePolicy.objects.filter(published=True).exists():
            self.stdout.write(self.style.WARNING(
                "  a policy is already published — nothing seeded"))
            return

        policy = administration.draft_policy(
            version=version,
            effective_from=date(year, 1, 1),
            note="Seeded from the ELM specification. Review before a real year opens.",
        )
        for category, credit, carries, cap, faculty in ENTITLEMENTS:
            administration.set_category_rule(
                policy=policy, category=category, annual_credit=credit,
                carries_forward=carries, carry_forward_cap=cap,
                applies_to_faculty=faculty)

        for category in Category:
            escalates = category not in UNIT_HEAD_FINAL
            AuthorityRule.objects.get_or_create(
                policy_id=policy.pk, category=category.value, unit="", designation="",
                defaults={
                    "establishment_step": escalates,
                    "sanctioning_designation": (
                        opts["sanctioning_designation"] if escalates else ""),
                })

        calendar = self._calendar(year)

        if opts["draft_only"]:
            self.stdout.write(self.style.WARNING(
                f"  drafted {version} and the {year} calendar — neither is published"))
            return

        administration.publish_policy(policy=policy, actor_user_id=0)
        with suppress(ConflictError):     # already published by an earlier run
            administration.publish_calendar(calendar=calendar, actor_user_id=0)

        self.stdout.write(
            f"  policy      {version}\n"
            f"  categories  {len(ENTITLEMENTS)}\n"
            f"  routing     {len(list(Category))} rule(s), "
            f"{opts['sanctioning_designation']} sanctions where it escalates\n"
            f"  calendar    {year}\n")
        self.stdout.write(self.style.SUCCESS("  leave is ready to accept applications"))
        self.stdout.write(
            "  Holidays and vacation periods are institute data — add them under "
            "Policy & Calendar before RH or VL can be applied for.")

    def _calendar(self, year: int) -> HolidayCalendar:
        existing = HolidayCalendar.objects.filter(year=year).first()
        if existing:
            return existing
        calendar = administration.draft_calendar(year=year, version="1")
        # A calendar cannot be published empty; Republic Day needs no local decision.
        administration.add_holiday(
            calendar=calendar, day=date(year, 1, 26), name="Republic Day")
        return calendar
