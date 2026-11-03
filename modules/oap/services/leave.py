from datetime import date
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.oap.domain import constants as c
from modules.oap.domain.state_machine import (
    InvalidStateTransitionError,
    LeaveStateMachine,
)
from modules.oap.domain.validation import (
    DomainValidationError,
    validate_leave_request,
)
from modules.oap.models.leave import LeaveAttachment, StudentLeaveApplication
from modules.oap.selectors.leave import get_leave_by_id
from modules.oap.services.notify import emit_notification


def submit_leave_application(
    user_id: int,
    department: str,
    programme: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    attachments: list[dict] | None = None,
) -> StudentLeaveApplication:
    """Submits a student leave application for HoD review (OA-UC-01, BW-OAP-01, BW-OAP-02)."""
    try:
        validate_leave_request(start_date, end_date, reason)
    except DomainValidationError as exc:
        raise BadRequestError(str(exc)) from exc

    application = StudentLeaveApplication.objects.create(
        user_id=user_id,
        department=department,
        programme=programme,
        leave_type=leave_type or "Casual Leave",
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=LeaveStateMachine.initial_state(),
    )

    if attachments:
        for att in attachments:
            file_name = att.get("file_name", "document")
            file_url = att.get("file_url", "")
            LeaveAttachment.objects.create(
                leave_application=application,
                file_name=file_name,
                file_url=file_url,
            )

    emit_notification(
        recipient_user_id=user_id,
        title="Leave Application Submitted",
        message=f"Your leave application from {start_date} to {end_date} has been submitted for HoD review.",
        related_entity_type="leave",
        related_entity_id=application.id,
    )

    return application


def decide_leave_application(
    leave_id: int,
    hod_user_id: int,
    decision: str,
    remarks: str = "",
) -> StudentLeaveApplication:
    """HoD approves or rejects a student leave application (OA-UC-03, OA-BR-11)."""
    application = get_leave_by_id(leave_id)
    if not application:
        raise NotFoundError(f"Leave application {leave_id} not found.")

    try:
        new_status = LeaveStateMachine.transition_decision(application.status, decision)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    application.status = new_status
    application.decision_by_user_id = hod_user_id
    application.decision_remarks = remarks
    application.decided_at = timezone.now()
    application.save(update_fields=["status", "decision_by_user_id", "decision_remarks", "decided_at", "updated_at"])

    emit_notification(
        recipient_user_id=application.user_id,
        title=f"Leave Application {new_status.title()}",
        message=f"Your leave application has been {new_status} by the HoD. Remarks: {remarks or 'None'}",
        related_entity_type="leave",
        related_entity_id=application.id,
    )

    return application
