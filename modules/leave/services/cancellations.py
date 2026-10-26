"""Approved leave cancellation workflow (CW-EL-02, EL-UC-008)."""

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.entities import LeaveStatus, ReviewDecision
from modules.leave.domain.errors import DomainError
from modules.leave.domain.rules import validate_cancellation_allowed
from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveBalance


def request_cancellation(
    application_id: int,
    principal,
    reason: str,
) -> LeaveApplication:
    """Employee requests cancellation of approved leave before its start date (EL-UC-008)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.applicant_user_id != principal.user_id:
            raise ConflictError("You can only request cancellation for your own leave.")

        try:
            validate_cancellation_allowed(
                leave_status=app.status,
                start_date=app.start_date,
                today=date.today(),
            )
        except DomainError as e:
            raise ConflictError(e.message) from None

        from_status = app.status
        app.status = LeaveStatus.AWAITING_CANCELLATION.value
        app.is_cancellation_requested = True
        app.cancellation_reason = reason
        app.save(
            update_fields=[
                "status",
                "is_cancellation_requested",
                "cancellation_reason",
                "updated_at",
            ]
        )

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="REQUEST_CANCELLATION",
            from_status=from_status,
            to_status=LeaveStatus.AWAITING_CANCELLATION.value,
            remarks=reason,
        )

        return app


def review_cancellation(
    application_id: int,
    principal,
    decision: str,
    remarks: str = "",
) -> LeaveApplication:
    """Authority reviews cancellation request."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.status != LeaveStatus.AWAITING_CANCELLATION.value:
            raise ConflictError("Application is not in AWAITING_CANCELLATION.")

        from_status = app.status

        if decision == ReviewDecision.APPROVED.value:
            app.status = LeaveStatus.CANCELLED.value
            # Restore deducted balance!
            bal = LeaveBalance.objects.select_for_update().get(
                user_id=app.applicant_user_id,
                year=app.start_date.year,
                leave_type=app.leave_type,
            )
            bal.balance += app.days_count
            bal.availed -= app.days_count
            bal.save(update_fields=["balance", "availed", "updated_at"])
        else:
            # Rejection preserves original APPROVED leave
            app.status = LeaveStatus.APPROVED.value
            app.is_cancellation_requested = False

        app.save(update_fields=["status", "is_cancellation_requested", "updated_at"])

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="REVIEW_CANCELLATION",
            from_status=from_status,
            to_status=app.status,
            remarks=f"Cancellation {decision}: {remarks}".strip(),
        )

        return app
