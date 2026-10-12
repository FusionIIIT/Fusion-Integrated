"""Substitute eligibility (BR-EL-014).

When a leave request requires responsibility coverage, exactly one substitute
is nominated. The nominee must be another employee - never the applicant - and
must hold no pending or approved leave that overlaps the responsibility period.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain.overlap import Interval, conflicts_with


@dataclass(frozen=True)
class SubstituteDecision:
    eligible: bool
    reason: str


def check_nomination(
    *,
    coverage_required: bool,
    applicant_id: int,
    nominee_ids: tuple[int, ...],
    nominee_leave: tuple[Interval, ...],
    period: Interval,
) -> SubstituteDecision:
    """BR-EL-014 - decide whether the nomination may proceed.

    ``period`` is the responsibility interval; it must be marked active so the
    nominee's leave is compared against it. ``nominee_leave`` is the nominated
    employee's own pending/approved leave.
    """
    if not coverage_required:
        return SubstituteDecision(True, "coverage_not_required")
    if not nominee_ids:
        return SubstituteDecision(False, "substitute_required")
    if len(nominee_ids) > 1:
        return SubstituteDecision(False, "exactly_one_substitute")
    if nominee_ids[0] == applicant_id:
        return SubstituteDecision(False, "substitute_is_applicant")
    if conflicts_with(period, nominee_leave):
        return SubstituteDecision(False, "substitute_has_overlapping_leave")
    return SubstituteDecision(True, "eligible")
