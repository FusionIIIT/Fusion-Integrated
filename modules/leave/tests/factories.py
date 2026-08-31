"""Fixtures: a published policy, a calendar and an authority configuration."""
from datetime import date
from decimal import Decimal

from modules.leave.domain.categories import Category
from modules.leave.models import (
    AuthorityRule,
    CategoryRule,
    EntryReason,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LedgerEntry,
    VacationPeriod,
)

YEAR = 2026
D = Decimal


def make_policy(**overrides) -> LeavePolicy:
    policy = LeavePolicy.objects.create(
        version=overrides.pop("version", "2026.1"),
        effective_from=overrides.pop("effective_from", date(YEAR, 1, 1)),
        published=True,
        # These tests work in fixed dates inside YEAR so the arithmetic stays
        # readable, and YEAR drifts into the past as time passes. The
        # back-dating rule has its own tests against the real default of 0.
        max_backdate_days=overrides.pop("max_backdate_days", 100_000),
        **overrides,
    )
    for category, credit, carries, faculty in (
        (Category.CL, 8, False, None),
        (Category.RH, 2, False, None),
        (Category.SCL, 15, False, None),
        (Category.EL, 30, True, False),
        (Category.EL, 0, True, True),
        (Category.COL, 20, True, None),
        (Category.VL, 60, False, True),
    ):
        CategoryRule.objects.create(
            policy=policy,
            category=category.value,
            annual_credit=D(credit),
            carries_forward=carries,
            applies_to_faculty=faculty,
        )
    return policy


def make_calendar(year: int = YEAR) -> HolidayCalendar:
    calendar = HolidayCalendar.objects.create(year=year, version="1", published=True)
    Holiday.objects.create(calendar=calendar, day=date(year, 8, 15), name="Independence Day")
    Holiday.objects.create(
        calendar=calendar, day=date(year, 10, 2), name="Optional festival", restricted=True
    )
    VacationPeriod.objects.create(
        calendar=calendar,
        name="Summer",
        starts_on=date(year, 5, 15),
        ends_on=date(year, 6, 30),
    )
    return calendar


def make_authority(policy, **overrides) -> None:
    """Unit head final for CL and RH; everything else escalates."""
    for category in Category:
        higher = category not in (Category.CL, Category.RH)
        AuthorityRule.objects.create(
            policy_id=policy.pk,
            category=category.value,
            establishment_step=higher and overrides.get("establishment_step", True),
            sanctioning_designation="Registrar" if higher else "",
        )


def credit(user_id: int, category: Category, days, year: int = YEAR) -> LedgerEntry:
    """Put this person on `days` of this category.

    Sets rather than adds, and is safe to call twice. The ledger allows one
    annual credit per category per year -- so a helper that appended a second
    one was writing state the service can never produce, and started failing
    the moment the database began enforcing it.
    """
    entry, created = LedgerEntry.objects.get_or_create(
        user_id=user_id,
        year=year,
        category=category.value,
        reason=EntryReason.ANNUAL_CREDIT,
        defaults={"days": D(days)},
    )
    if not created and entry.days != D(days):
        entry.days = D(days)
        entry.save(update_fields=["days", "updated_at"])
    return entry


def setup_all(user_id: int = 501):
    policy = make_policy()
    calendar = make_calendar()
    make_authority(policy)
    for category, days in ((Category.CL, 8), (Category.EL, 30), (Category.COL, 20)):
        credit(user_id, category, days)
    return policy, calendar
