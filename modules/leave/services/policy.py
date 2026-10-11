"""Load the currently effective published policy and calendar (BR-EL-030/031)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from core.api.exceptions import ConflictError
from modules.leave.domain.calendar import PublishedCalendar
from modules.leave.domain.eligibility import PolicySnapshot, canonical_policy
from modules.leave.models import HolidayCalendar, LeavePolicy


def effective_policy() -> tuple[LeavePolicy, PolicySnapshot]:
    row = LeavePolicy.objects.filter(is_effective=True, published_at__isnull=False).first()
    if row is None:
        raise ConflictError(
            "No published leave policy is in force. A Leave Administrator must publish one.",
            code="BR-EL-030")
    cats = row.categories_requiring_substitute or []
    snap = PolicySnapshot(
        cl_annual=row.cl_annual,
        rh_annual=row.rh_annual,
        scl_annual=row.scl_annual,
        el_staff_annual=row.el_staff_annual,
        vl_faculty=row.vl_faculty,
        col_annual=row.col_annual,
        vl_to_el_ratio=(row.vl_to_el_numerator, row.vl_to_el_denominator),
        categories_requiring_substitute=frozenset(cats),
        establishment_step_enabled=row.establishment_step_enabled,
        col_requires_medical=row.col_requires_medical,
        sla_reminder_hours=row.sla_reminder_hours,
        sla_escalation_hours=row.sla_escalation_hours,
    )
    return row, snap


def effective_calendar() -> PublishedCalendar:
    row = HolidayCalendar.objects.filter(
        is_effective=True, published_at__isnull=False,
    ).prefetch_related("entries").first()
    if row is None:
        raise ConflictError(
            "No published holiday/RH calendar is in force. A Leave Administrator must publish one.",
            code="BR-EL-031")
    closed: set[date] = set()
    rh: set[date] = set()
    vacations: list[tuple[date, date]] = []
    for e in row.entries.all():
        if e.kind == "vacation":
            vacations.append((e.start_on, e.end_on))
            continue
        d = e.start_on
        while d <= e.end_on:
            if e.kind == "closed":
                closed.add(d)
            elif e.kind == "rh":
                rh.add(d)
            d += timedelta(days=1)
    return PublishedCalendar(frozenset(closed), frozenset(rh), tuple(vacations))


def snapshot_from_canonical() -> PolicySnapshot:
    return canonical_policy()


def seed_baseline(*, year: int, actor_user_id: int | None = None) -> None:
    """Idempotent baseline so first use has an effective policy and calendar."""
    from django.utils import timezone

    if not LeavePolicy.objects.filter(is_effective=True).exists():
        base = canonical_policy()
        LeavePolicy.objects.create(
            version=1, label="Study baseline", published_at=timezone.now(),
            published_by_user_id=actor_user_id, is_effective=True,
            cl_annual=base.cl_annual, rh_annual=base.rh_annual,
            scl_annual=base.scl_annual, el_staff_annual=base.el_staff_annual,
            vl_faculty=base.vl_faculty, col_annual=base.col_annual,
            categories_requiring_substitute=sorted(base.categories_requiring_substitute),
            establishment_step_enabled=base.establishment_step_enabled,
            col_requires_medical=base.col_requires_medical,
            sla_reminder_hours=base.sla_reminder_hours,
            sla_escalation_hours=base.sla_escalation_hours,
        )
    if not HolidayCalendar.objects.filter(is_effective=True).exists():
        HolidayCalendar.objects.create(
            version=1, year=year, label="Study baseline calendar",
            published_at=timezone.now(), published_by_user_id=actor_user_id,
            is_effective=True,
        )
