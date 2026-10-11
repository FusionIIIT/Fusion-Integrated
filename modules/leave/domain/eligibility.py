"""Category eligibility and request validation (BR-EL-001..015, BR-EL-030/031)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.leave.domain.calendar import PublishedCalendar
from modules.leave.domain.categories import (
    CATEGORIES, CL, COL, EL, HALVES, RH, SCL, VL,
)
from modules.leave.domain.counting import chargeable_days

FACULTY = "faculty"
STAFF = "staff"
EMPLOYEE_KINDS = frozenset({FACULTY, STAFF})


@dataclass(frozen=True)
class PolicySnapshot:
    """Currently effective published policy parameters (BR-EL-030)."""
    cl_annual: Decimal
    rh_annual: Decimal
    scl_annual: Decimal
    el_staff_annual: Decimal
    vl_faculty: Decimal
    col_annual: Decimal
    vl_to_el_ratio: tuple[int, int]  # 2 VL : 1 EL
    categories_requiring_substitute: frozenset[str]
    establishment_step_enabled: bool
    col_requires_medical: bool
    sla_reminder_hours: int
    sla_escalation_hours: int


def canonical_policy() -> PolicySnapshot:
    """Study baseline numbers (BR-EL-002..009, SRS-EL-009..030)."""
    return PolicySnapshot(
        cl_annual=Decimal("8"),
        rh_annual=Decimal("2"),
        scl_annual=Decimal("15"),
        el_staff_annual=Decimal("30"),
        vl_faculty=Decimal("60"),
        col_annual=Decimal("20"),
        vl_to_el_ratio=(2, 1),
        categories_requiring_substitute=frozenset({SCL, EL, COL, VL}),
        establishment_step_enabled=True,
        col_requires_medical=True,
        sla_reminder_hours=48,
        sla_escalation_hours=96,
    )


@dataclass(frozen=True)
class LeaveRequest:
    category: str
    start: date
    end: date
    half: str | None
    station_leave: bool
    medical_evidence: bool
    purpose: str
    applicant_kind: str  # faculty | staff
    requires_substitute: bool


@dataclass(frozen=True)
class OccupiedInterval:
    start: date
    end: date
    half: str | None
    category: str


class ValidationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def category_allowed(kind: str, category: str, policy: PolicySnapshot) -> bool:
    """BR-EL-001 plus faculty/staff differences in BR-EL-005/006."""
    if kind not in EMPLOYEE_KINDS:
        return False
    if category not in CATEGORIES:
        return False
    if category == VL:
        return kind == FACULTY
    return True


def overlaps(a: OccupiedInterval, b: OccupiedInterval) -> bool:
    """BR-EL-012: different halves of same-day CL do not overlap."""
    if a.end < b.start or b.end < a.start:
        return False
    if (a.start == a.end == b.start == b.end
            and a.half in HALVES and b.half in HALVES
            and a.half != b.half
            and a.category == CL and b.category == CL):
        return False
    return True


def validate_request(*, request: LeaveRequest, policy: PolicySnapshot,
                     calendar: PublishedCalendar,
                     balance: Decimal,
                     occupied: tuple[OccupiedInterval, ...],
                     ) -> Decimal:
    if not category_allowed(request.applicant_kind, request.category, policy):
        raise ValidationError("BR-EL-001",
                              "This leave category is not available to the applicant.")
    if not request.purpose.strip():
        raise ValidationError("SRS-EL-003", "A purpose/reason is required.")
    if request.category == CL and request.half not in (None, *HALVES):
        raise ValidationError("BR-EL-010", "Half-day CL must be first or second half.")
    if request.category != CL and request.half:
        raise ValidationError("BR-EL-010", "Half-day applies only to CL.")
    if request.category == RH:
        if request.start != request.end:
            raise ValidationError("BR-EL-003", "RH must fall on a single published date.")
        if not calendar.is_restricted_holiday(request.start):
            raise ValidationError("BR-EL-003",
                                  "RH must correspond to an applicable published Restricted Holiday.")
    if request.category == VL:
        if not calendar.in_vacation(request.start, request.end):
            raise ValidationError("BR-EL-006",
                                  "VL may be availed only during an applicable vacation period.")
    if request.category == COL and policy.col_requires_medical and not request.medical_evidence:
        raise ValidationError("BR-EL-009",
                              "COL requires supporting medical evidence.")

    days = chargeable_days(
        category=request.category, start=request.start, end=request.end,
        half=request.half, closed_holidays=calendar.closed,
    )
    if days > balance:
        raise ValidationError("SRS-EL-007",
                              "Requested days exceed the available leave entitlement.")

    proposed = OccupiedInterval(request.start, request.end, request.half, request.category)
    for other in occupied:
        if overlaps(proposed, other):
            raise ValidationError("BR-EL-012",
                                  "This request overlaps another pending or approved leave.")
    return days
