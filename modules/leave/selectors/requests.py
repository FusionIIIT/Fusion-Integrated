"""Queries for leave requests and overlap checks."""

from __future__ import annotations

import datetime

from modules.leave.domain.rules import validate_overlap
from modules.leave.models import LeaveRequest

ACTIVE_STATES = frozenset(
    {
        "submitted_pending_substitute",
        "pending_review",
        "pending_routing",
        "pending_sanction",
        "approved",
        "cancellation_pending_review",
        "cancellation_pending_routing",
        "cancellation_pending_sanction",
        "extension_pending_substitute",
        "extension_pending_review",
        "extension_pending_routing",
        "extension_pending_sanction",
        "resumption_pending",
    }
)


def get_request_by_id(request_id: int) -> LeaveRequest | None:
    return LeaveRequest.objects.filter(pk=request_id).first()


def check_applicant_overlap(
    user_id: int,
    starts_on: datetime.date,
    ends_on: datetime.date,
    half: str,
    exclude_id: int | None = None,
) -> None:
    """Verifies no impermissible overlap under BR-EL-012."""
    qs = LeaveRequest.objects.filter(user_id=user_id, state__in=ACTIVE_STATES)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    existing = [(r.starts_on, r.ends_on, r.half) for r in qs]
    validate_overlap(starts_on, ends_on, half, existing)


def check_substitute_availability(
    substitute_id: int, starts_on: datetime.date, ends_on: datetime.date
) -> bool:
    """Checks whether substitute has overlapping active leave under BR-EL-014."""
    overlap = LeaveRequest.objects.filter(
        user_id=substitute_id,
        state__in=ACTIVE_STATES,
        starts_on__lte=ends_on,
        ends_on__gte=starts_on,
    ).exists()
    return not overlap
