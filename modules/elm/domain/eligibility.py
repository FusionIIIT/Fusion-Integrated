"""Who may ask for what (BR-EL-001, 003, 006, 014)."""
from __future__ import annotations

from collections.abc import Collection
from datetime import date, timedelta

from modules.elm.domain import leave_types as lt
from modules.elm.domain.errors import RuleViolation


def check_category(kind: str, leave_type: str) -> None:
    if leave_type not in lt.eligible_types(kind):
        raise RuleViolation(
            f"{leave_type} is not available to a {kind or 'unknown'} employee.", "BR-EL-001")


def check_restricted_holiday(day: date, published: Collection[date]) -> None:
    if day not in published:
        raise RuleViolation("That date is not a published restricted holiday.", "BR-EL-003")


def check_vacation_periods(start: date, end: date,
                           periods: Collection[tuple[date, date]]) -> None:
    """Every day of a VL request must fall inside a published vacation period."""
    day = start
    while day <= end:
        if not any(p_start <= day <= p_end for p_start, p_end in periods):
            raise RuleViolation(
                "VL can be taken only inside a published vacation period.", "BR-EL-006")
        day += timedelta(days=1)


def check_substitute(applicant_id: int, substitute_id: int, *, substitute_is_employee: bool,
                     substitute_has_overlap: bool) -> None:
    if substitute_id == applicant_id:
        raise RuleViolation("You cannot nominate yourself as substitute.", "BR-EL-014")
    if not substitute_is_employee:
        raise RuleViolation("The substitute must be an employee.", "BR-EL-014")
    if substitute_has_overlap:
        raise RuleViolation(
            "The substitute has leave during that period.", "BR-EL-014")


def check_medical_evidence(leave_type: str, evidence: str) -> None:
    if leave_type in lt.NEEDS_MEDICAL_EVIDENCE and not evidence.strip():
        raise RuleViolation("COL needs a supporting medical reference.", "BR-EL-009")
