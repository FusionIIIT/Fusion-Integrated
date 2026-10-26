"""Resumption of duty submission and review (CW-EL-04, EL-UC-010, EL-UC-011)."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.entities import LeaveCategory, ResumptionStatus
from modules.leave.domain.errors import DomainError
from modules.leave.domain.rules import calculate_resumption_adjustment, validate_resumption_allowed
from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveBalance
from modules.leave.selectors.calendar import get_closed_holiday_dates


def submit_resumption(
    application_id: int,
    principal,
    actual_resumption_date: date,
    remarks: str = "",
) -> LeaveApplication:
    """Employee submits actual resumption date after EL/COL/VL (EL-UC-010, BR-EL-027)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.applicant_user_id != principal.user_id:
            raise ConflictError("You can only submit resumption for your own leave.")

        if app.leave_type not in (
            LeaveCategory.EL.value,
            LeaveCategory.COL.value,
            LeaveCategory.VL.value,
        ):
            raise ConflictError("Formal resumption is only supported for EL, COL, and VL.")

        if app.status != "APPROVED":
            raise ConflictError("Resumption can only be submitted for approved leaves.")

        try:
            validate_resumption_allowed(app.start_date, actual_resumption_date)
        except DomainError as e:
            raise ConflictError(e.message) from None

        app.resumption_status = ResumptionStatus.SUBMITTED.value
        app.actual_resumption_date = actual_resumption_date
        app.resumption_remarks = remarks
        app.save(
            update_fields=[
                "resumption_status",
                "actual_resumption_date",
                "resumption_remarks",
                "updated_at",
            ]
        )

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="SUBMIT_RESUMPTION",
            from_status="APPROVED",
            to_status="APPROVED",
            remarks=f"Actual return date: {actual_resumption_date}. {remarks}".strip(),
        )

        return app


def review_resumption(
    application_id: int,
    principal,
    remarks: str = "",
) -> LeaveApplication:
    """Sanctioning Authority reviews resumption and adjusts balance (EL-UC-011, BR-EL-028)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.resumption_status != ResumptionStatus.SUBMITTED.value:
            raise ConflictError("Resumption is not pending review.")

        closed = get_closed_holiday_dates(app.start_date.year)
        adjustment = calculate_resumption_adjustment(
            approved_start=app.start_date,
            approved_end=app.end_date,
            actual_resumption_date=app.actual_resumption_date,
            category=app.leave_type,
            closed_holiday_dates=closed,
        )

        if adjustment != Decimal("0.0"):
            bal = LeaveBalance.objects.select_for_update().get(
                user_id=app.applicant_user_id,
                year=app.start_date.year,
                leave_type=app.leave_type,
            )
            # Positive adjustment means more days availed -> deduct balance
            # Negative adjustment means fewer days availed -> refund balance
            bal.balance -= adjustment
            bal.availed += adjustment
            bal.save(update_fields=["balance", "availed", "updated_at"])

        app.resumption_status = ResumptionStatus.REVIEWED.value
        app.resumption_days_adjusted = adjustment
        app.save(update_fields=["resumption_status", "resumption_days_adjusted", "updated_at"])

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="REVIEW_RESUMPTION",
            from_status="APPROVED",
            to_status="APPROVED",
            remarks=f"Resumption reviewed. Days adjustment: {adjustment}. {remarks}".strip(),
        )

        return app
