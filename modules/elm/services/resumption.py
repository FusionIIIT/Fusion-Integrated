"""Resumption of duty services (EL-UC-010, EL-UC-011, CW-EL-04).

Enforces BR-EL-027 and BR-EL-028.
"""
from __future__ import annotations

import datetime
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.constants import CONTINUOUS_COUNT_CATEGORIES, LeaveCategory
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.state_machine import evaluate_resumption
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveResumptionReport
from modules.elm.services.audit import record_audit


def submit_resumption(
    actor,
    application_id: int,
    actual_resumption_date: datetime.date,
    reason_for_difference: str = "",
) -> LeaveResumptionReport:
    """Employee declares actual return to duty after EL, COL, or VL (EL-UC-010, BR-EL-027)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().select_related("leave_type").get(id=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError("Leave application not found.", code="not_found")

        if app.employee_id != user_id:
            raise PermissionDeniedError("Cannot submit resumption for another employee's leave.", code="permission_denied")

        if app.status != "APPROVED":
            raise ConflictError("Resumption can only be submitted for APPROVED leave.", code="invalid_state")

        if LeaveCategory(app.leave_type.code) not in CONTINUOUS_COUNT_CATEGORIES:
            raise BadRequestError(
                f"Resumption review applies only to EL, COL, and VL, not '{app.leave_type.code}'.",
                code="invalid_category",
            )

        if LeaveResumptionReport.objects.filter(application=app, status="SUBMITTED").exists():
            raise ConflictError("A resumption report is already pending review.", code="already_submitted")

        resumption_type, diff_days = evaluate_resumption(
            approved_end_date=app.end_date,
            actual_resumption_date=actual_resumption_date,
        )

        rep = LeaveResumptionReport.objects.create(
            application=app,
            employee_id=user_id,
            actual_resumption_date=actual_resumption_date,
            resumption_type=resumption_type.value,
            adjusted_days=diff_days,
            reason_for_difference=reason_for_difference,
            status="SUBMITTED",
        )

        record_audit(
            application=app,
            actor_id=user_id,
            action="SUBMIT_RESUMPTION",
            from_status=app.status,
            to_status=app.status,
            remarks=f"Resumed duty on {actual_resumption_date} ({resumption_type.value}).",
        )

    return rep


def review_resumption(
    actor,
    resumption_id: int,
    remarks: str = "",
) -> LeaveResumptionReport:
    """Sanctioning authority reviews resumption and synchronizes balance (EL-UC-011, BR-EL-028)."""
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    with transaction.atomic():
        try:
            rep = LeaveResumptionReport.objects.select_for_update().select_related("application", "application__leave_type").get(id=resumption_id)
        except LeaveResumptionReport.DoesNotExist:
            raise NotFoundError("Resumption report not found.", code="not_found")

        app = rep.application
        if app.employee_id == user_id:
            raise PermissionDeniedError("Cannot review own resumption report.", code="self_review")

        if rep.status != "SUBMITTED":
            raise ConflictError("Resumption report is already reviewed.", code="already_reviewed")

        balance = LeaveBalance.objects.select_for_update().get(
            employee_id=app.employee_id,
            leave_type=app.leave_type,
            year=app.start_date.year,
        )

        # BR-EL-028: Apply balance and actual leave period adjustments
        if rep.resumption_type == "EARLY":
            # Employee returned early: refund unused days
            balance.used = max(0.0, float(balance.used) - float(rep.adjusted_days))
            balance.save(update_fields=["used", "updated_at"])
            # Update application end date and days to actual
            app.end_date = rep.actual_resumption_date - datetime.timedelta(days=1)
            app.days = max(0.0, float(app.days) - float(rep.adjusted_days))
            app.save(update_fields=["end_date", "days", "updated_at"])

        elif rep.resumption_type == "LATE":
            # Employee returned late: deduct additional days
            balance.used += rep.adjusted_days
            balance.save(update_fields=["used", "updated_at"])
            app.end_date = rep.actual_resumption_date - datetime.timedelta(days=1)
            app.days += rep.adjusted_days
            app.save(update_fields=["end_date", "days", "updated_at"])

        # If NORMAL: no adjustment to leave period or balance (BR-EL-028)

        rep.status = "REVIEWED"
        rep.reviewer_id = user_id
        rep.remarks = remarks
        rep.reviewed_at = timezone.now()
        rep.save()

        record_audit(
            application=app,
            actor_id=user_id,
            action=f"RESUMPTION_REVIEWED_{rep.resumption_type}",
            from_status="APPROVED",
            to_status="APPROVED",
            remarks=remarks,
        )

    return rep
