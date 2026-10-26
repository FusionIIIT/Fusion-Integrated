"""Transactional leave withdrawal workflow."""

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.elm.models import LeaveAuditEvent, LeaveRequest


@transaction.atomic
def withdraw_leave_request(*, request_id: int, actor_id: int) -> LeaveRequest:
    leave = LeaveRequest.objects.select_for_update().filter(
        pk=request_id
    ).first()

    if leave is None:
        raise ConflictError("Leave request not found.", code="not_found")

    if leave.employee_id != actor_id:
        raise ConflictError(
            "You can only withdraw your own leave request.",
            code="withdraw_forbidden",
        )

    if leave.status != LeaveRequest.Status.PENDING:
        raise ConflictError(
            "Only pending leave requests can be withdrawn.",
            code="request_not_pending",
        )

    previous_status = leave.status
    leave.status = LeaveRequest.Status.WITHDRAWN
    leave.save(update_fields=["status", "updated_at"])

    LeaveAuditEvent.objects.create(
        leave_request=leave,
        actor_id=actor_id,
        action="WITHDRAWN",
        details={"previous_status": previous_status},
    )

    return leave
