"""Approved leave cancellation services (EL-UC-008, CW-EL-02).

Enforces BR-EL-023 and BR-EL-024.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import ApplicationStatus, LeaveCategory
from modules.elm.domain.state_machine import validate_cancellation_request
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveCancellationRequest
from modules.elm.services.audit import record_audit


def request_cancellation(
    actor,
    application_id: int,
    reason: str,
) -> LeaveCancellationRequest:
    """Employee requests cancellation of approved leave before start date (EL-UC-008, BR-EL-023)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id != user_id:
            raise PermissionDeniedError("Cannot request cancellation of another employee's leave.", code="permission_denied")

        try:
            validate_cancellation_request(
                current_status=ApplicationStatus(app.status),
                start_date=app.start_date,
                today=timezone.now().date(),
            )
        except Exception as exc:
            raise ConflictError(str(exc), code="invalid_cancellation") from exc

        if LeaveCancellationRequest.objects.filter(application=app, status__in=["PENDING_UNIT_HEAD", "PENDING_ESTABLISHMENT", "PENDING_SANCTION"]).exists():
            raise ConflictError("A cancellation request is already pending for this leave.", code="already_pending")

        cancel_req = LeaveCancellationRequest.objects.create(
            application=app,
            employee_id=user_id,
            reason=reason,
            status="PENDING_UNIT_HEAD",
        )

        record_audit(
            application=app,
            actor_id=user_id,
            action="REQUEST_CANCELLATION",
            from_status=app.status,
            to_status=app.status,
            remarks=reason,
        )

    return cancel_req


def decide_cancellation(
    actor,
    cancellation_id: int,
    approve: bool,
    remarks: str = "",
    is_final_authority: bool = False,
) -> LeaveCancellationRequest:
    """Review and decide on cancellation request (BR-EL-023)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            cancel_req = LeaveCancellationRequest.objects.select_for_update().select_related("application", "application__leave_type").get(id=cancellation_id)
        except LeaveCancellationRequest.DoesNotExist:
            raise NotFoundError("Cancellation request not found.", code="not_found")

        app = cancel_req.application
        if app.employee_id == user_id:
            raise PermissionDeniedError("Cannot decide on own cancellation request.", code="self_review")

        # Determine if Unit Head is final (for CL/RH, Unit Head is final: BR-EL-016)
        is_cl_rh = app.leave_type.code in (LeaveCategory.CL.value, LeaveCategory.RH.value)
        can_finalize = is_cl_rh or is_final_authority

        if can_finalize:
            if approve:
                # Restore leave balance!
                balance = LeaveBalance.objects.select_for_update().get(
                    employee_id=app.employee_id,
                    leave_type=app.leave_type,
                    year=app.start_date.year,
                )
                balance.used -= app.days
                balance.save(update_fields=["used", "updated_at"])

                app.status = "CANCELLED"
                app.save(update_fields=["status", "updated_at"])
                cancel_req.status = "APPROVED"
                action_name = "CANCELLATION_APPROVED"
            else:
                # Rejection leaves original approval unchanged!
                cancel_req.status = "REJECTED"
                action_name = "CANCELLATION_REJECTED"

            cancel_req.approver_id = user_id
            cancel_req.remarks = remarks
            cancel_req.decided_at = timezone.now()
            cancel_req.save()

            record_audit(
                application=app,
                actor_id=user_id,
                action=action_name,
                from_status="APPROVED",
                to_status=app.status,
                remarks=remarks,
            )
        else:
            # Forwarding higher-sanction cancellation
            cancel_req.status = "PENDING_SANCTION"
            cancel_req.unit_head_recommendation = "RECOMMENDED" if approve else "NOT_RECOMMENDED"
            cancel_req.remarks = remarks
            cancel_req.save()

            record_audit(
                application=app,
                actor_id=user_id,
                action="CANCELLATION_FORWARDED",
                from_status="APPROVED",
                to_status="APPROVED",
                remarks=remarks,
            )

    return cancel_req
