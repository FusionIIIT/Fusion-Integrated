"""Leave request cancellation service (HR-UC-003 / permission leave.request.delete)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest


def cancel_leave_request(
    request_id: int,
    user_id: int,
    reason: str = "",
    is_admin_override: bool = False,
) -> LeaveRequest:
    """Cancel an in-flight pending leave request by the submitting applicant.

    Enforces:
    - Ownership: only the applicant (or admin override) may cancel
    - Lifecycle: only pending requests may be cancelled
    - State machine: transition from PENDING_CURRENT_AUTHORITY -> CANCELLED
    """
    with transaction.atomic():
        req = (
            LeaveRequest.objects.select_for_update()
            .filter(id=request_id)
            .first()
        )
        if not req:
            raise NotFoundError(f"Leave request #{request_id} not found.")

        if not is_admin_override and req.user_id != user_id:
            raise PermissionDeniedError("You can only cancel your own leave requests.")

        if req.status != LeaveRequest.Status.PENDING_CURRENT_AUTHORITY:
            raise ConflictError(
                f"Cannot cancel leave request in status {req.status!r}; "
                f"only pending requests can be cancelled."
            )

        sm.resolve(sm.PENDING_CURRENT_AUTHORITY, sm.CANCELLED, sm.APPLICANT)

        req.status = LeaveRequest.Status.CANCELLED
        req.cancellation_reason = reason.strip()
        req.save(update_fields=["status", "cancellation_reason", "updated_at"])

    return req
