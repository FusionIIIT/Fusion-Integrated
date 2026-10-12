"""Leave policy: the one row every entitlement and gate reads.

BR-EL-030 gives this table no draft/publish lifecycle (unlike the holiday
calendar): editing the policy is immediate and fully audited by the admin
action itself. Defaults mirror the ELM baseline §2–4.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


def _substitute_defaults() -> list[str]:
    """BR-EL-014: EL, COL and VL carry a responsibility that needs covering."""
    return ["el", "col", "vl"]


class LeavePolicy(TimeStampedModel):
    """Singleton (primary key is always 1); services use `get_or_create`."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)

    # Annual entitlements (baseline §2). EL for faculty comes from
    # vacation conversion instead of an annual credit (BR-EL-005).
    cl_annual = models.DecimalField(max_digits=5, decimal_places=2, default=8)
    rh_annual = models.DecimalField(max_digits=5, decimal_places=2, default=2)
    scl_annual = models.DecimalField(max_digits=5, decimal_places=2, default=15)
    el_annual_nonfaculty = models.DecimalField(
        max_digits=5, decimal_places=2, default=30)
    el_annual_faculty = models.DecimalField(
        max_digits=5, decimal_places=2, default=0)
    col_annual = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    vl_annual_faculty = models.DecimalField(
        max_digits=5, decimal_places=2, default=60)

    # BR-EL-005: 2 VL convert into 1 EL at year end.
    vl_to_el_numerator = models.PositiveSmallIntegerField(default=2)
    vl_to_el_denominator = models.PositiveSmallIntegerField(default=1)

    # BR-EL-007/008: which categories survive the boundary as themselves.
    el_carry_forward = models.BooleanField(default=True)
    col_carry_forward = models.BooleanField(default=True)

    # BR-EL-014/015: categories whose routing is gated on substitute consent.
    substitute_required_categories = models.JSONField(
        default=_substitute_defaults, blank=True)

    # SCL and COL evidence (PS §3): the clerk asks, the applicant supplies.
    scl_evidence_required = models.BooleanField(default=False)
    col_evidence_required = models.BooleanField(default=False)

    # The year boundary: leave "year" labels end on this month/day
    # (default 31 Dec, so 2026-12-31 leave belongs to leave-year 2026).
    year_end_month = models.PositiveSmallIntegerField(default=12)
    year_end_day = models.PositiveSmallIntegerField(default=31)

    class Meta:
        db_table = "leave_policy"

    def __str__(self) -> str:
        return "Leave policy"
