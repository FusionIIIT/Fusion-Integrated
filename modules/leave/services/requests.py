"""Transactional leave-request writes."""
from __future__ import annotations

from django.db import connection, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.requests import LeaveRuleError, RequestPeriod, overlaps, validate_request
from modules.leave.models import LeaveRequest
from modules.leave.selectors.requests import visible_request
from modules.leave.services.authz import require

P_CREATE = "leave.request.create"
P_DELETE = "leave.request.delete"


def _period(row: LeaveRequest) -> RequestPeriod:
    return RequestPeriod(row.category, row.starts_on, row.ends_on, row.cl_half)


def _lock_employee_requests(*, user_id: int) -> None:
    """Serialize overlapping-request checks for one employee on PostgreSQL.

    Locking matching rows does not protect the empty-query case. PostgreSQL is
    the only configured production database, so a transaction-scoped advisory
    lock supplies that missing predicate lock without a cross-module user row.
    Other backends retain row locking for development compatibility but are not
    concurrency-safe for this invariant.
    """
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [0x454C4D, user_id])


def create(*, actor, category: str, starts_on, ends_on, cl_half: str, reason: str,
           station_leave: bool = False, station_leave_details: str = "") -> LeaveRequest:
    require(actor, P_CREATE)
    candidate = RequestPeriod(category, starts_on, ends_on, cl_half)
    try:
        validate_request(period=candidate, reason=reason, station_leave=station_leave,
                         station_leave_details=station_leave_details)
    except LeaveRuleError as exc:
        raise ConflictError(str(exc), code="leave_validation_failed") from exc

    return _create_validated(
        actor=actor, candidate=candidate, reason=reason, station_leave=station_leave,
        station_leave_details=station_leave_details,
    )


@transaction.atomic
def _create_validated(*, actor, candidate: RequestPeriod, reason: str, station_leave: bool,
                      station_leave_details: str) -> LeaveRequest:

    _lock_employee_requests(user_id=actor.user_id)
    active = LeaveRequest.objects.select_for_update().filter(
        user_id=actor.user_id,
        status__in=[LeaveRequest.STATUS_PENDING, LeaveRequest.STATUS_APPROVED],
    )
    if any(overlaps(candidate, _period(row)) for row in active):
        raise ConflictError("This leave request overlaps an active request.",
                            code="leave_overlap")
    return LeaveRequest.objects.create(
        user_id=actor.user_id, category=candidate.category, starts_on=candidate.starts_on,
        ends_on=candidate.ends_on, cl_half=candidate.cl_half, reason=reason.strip(),
        station_leave=station_leave,
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
