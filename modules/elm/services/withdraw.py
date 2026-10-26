"""Withdrawal service (EL-UC-007).

Enforces BR-EL-022 and BR-EL-034.
"""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import ApplicationStatus
from modules.elm.domain.state_machine import validate_withdrawal
from modules.elm.models import LeaveApplication
from modules.elm.services.audit import record_audit


def withdraw_pending_request(
    actor,
    application_id: int,
    remarks: str = "Withdrawn by employee",
) -> LeaveApplication:
    """Immediate withdrawal of pending request before final approval (BR-EL-022)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id != user_id:
            raise PermissionDeniedError("Cannot withdraw another employee's application.", code="permission_denied")

        try:
            validate_withdrawal(ApplicationStatus(app.status))
        except Exception as exc:
            raise ConflictError(str(exc), code="invalid_state") from exc

        from_status = app.status
        app.status = "WITHDRAWN"

        # If a substitute was pending, close the task
        if app.substitute_status == "PENDING":
            app.substitute_status = "NONE"

        app.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action="WITHDRAW",
            from_status=from_status,
            to_status="WITHDRAWN",
            remarks=remarks,
        )

    return app
