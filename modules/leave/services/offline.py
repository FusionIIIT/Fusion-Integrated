"""Retrospective offline sanctioned leave recording (EL-UC-016, BR-EL-030)."""

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.entities import LeaveStatus
from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveBalance
from modules.leave.selectors.calendar import get_closed_holiday_dates
from modules.leave.services.balances import ensure_user_balances_initialized


def record_offline_leave(
    admin_principal,
    applicant_user_id: int,
    applicant_kind: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    sanction_ref: str,
    sanction_date: date,
    sanctioned_by: str,
    half_day_type: str = "FULL",
) -> LeaveApplication:
    """Record already-sanctioned offline leave for record synchronization."""
    with transaction.atomic():
        year = start_date.year
        ensure_user_balances_initialized(applicant_user_id, year, applicant_kind)

        closed = get_closed_holiday_dates(year)
        days = calculate_leave_days(
            category=leave_type,
            start_date=start_date,
            end_date=end_date,
            half_day_type=half_day_type,
            closed_holiday_dates=closed,
        )

        bal = LeaveBalance.objects.select_for_update().get(
            user_id=applicant_user_id,
            year=year,
            leave_type=leave_type,
        )
        if bal.balance < days:
            msg = f"Insufficient balance ({bal.balance}) for offline entry of {days} days."
            raise ConflictError(msg)

        bal.balance -= days
        bal.availed += days
        bal.save(update_fields=["balance", "availed", "updated_at"])

        app = LeaveApplication.objects.create(
            applicant_user_id=applicant_user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            half_day_type=half_day_type,
            days_count=days,
            reason=reason,
            status=LeaveStatus.APPROVED.value,
            is_offline=True,
            offline_sanction_ref=sanction_ref,
            offline_sanction_date=sanction_date,
            offline_sanctioned_by=sanctioned_by,
        )

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=admin_principal.user_id,
            action="OFFLINE_RECORD",
            from_status="OFFLINE",
            to_status=LeaveStatus.APPROVED.value,
            remarks=f"Retrospectively recorded. Sanction Ref: {sanction_ref}",
        )

        return app
