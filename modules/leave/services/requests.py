"""Transactional leave-request writes."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.requests import LeaveRuleError, RequestPeriod, overlaps, validate_period
from modules.leave.models import LeaveRequest
from modules.leave.selectors.requests import visible_request
from modules.leave.services.authz import require

P_CREATE = "leave.request.create"
P_DELETE = "leave.request.delete"


def _period(row: LeaveRequest) -> RequestPeriod:
    return RequestPeriod(row.category, row.starts_on, row.ends_on, row.cl_half)


@transaction.atomic
def create(*, actor, category: str, starts_on, ends_on, cl_half: str, reason: str,
           station_leave: bool = False, station_leave_details: str = "") -> LeaveRequest:
    require(actor, P_CREATE)
    candidate = RequestPeriod(category, starts_on, ends_on, cl_half)
    try:
        validate_period(candidate)
    except LeaveRuleError as exc:
        raise ConflictError(str(exc), code="leave_validation_failed") from exc

    pending = LeaveRequest.objects.select_for_update().filter(
        user_id=actor.user_id, status=LeaveRequest.STATUS_PENDING)
    if any(overlaps(candidate, _period(row)) for row in pending):
        raise ConflictError("This leave request overlaps a pending request.",
                            code="leave_overlap")
    return LeaveRequest.objects.create(
        user_id=actor.user_id, category=category, starts_on=starts_on, ends_on=ends_on,
        cl_half=cl_half, reason=reason.strip(), station_leave=station_leave,
        station_leave_details=station_leave_details.strip(),
    )


@transaction.atomic
def withdraw(*, actor, request_id: int) -> LeaveRequest:
    require(actor, P_DELETE)
    row = visible_request(principal=actor, request_id=request_id)
    if row is None:
        raise NotFoundError()
    if row.status != LeaveRequest.STATUS_PENDING:
        raise ConflictError("Only a pending leave request can be withdrawn.",
                            code="leave_not_pending")
    row.status = LeaveRequest.STATUS_WITHDRAWN
    row.withdrawn_at = timezone.now()
    row.save(update_fields=["status", "withdrawn_at", "updated_at"])
    return row
