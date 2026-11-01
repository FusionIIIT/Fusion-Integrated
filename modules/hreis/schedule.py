"""Scheduled maintenance tasks for HR-EIS (HR-UC-021, HR-UC-022)."""
from __future__ import annotations

from datetime import date, timedelta
from django.utils import timezone

from modules.hreis.models import (
    AppraisalSubmission,
    CpdaRequest,
    EmployeeServiceRecord,
    LeaveRequest,
    LtcRequest,
)
from modules.hreis.services.notifications import send_hr_notification
from modules.hreis.services.workflow_config import get_workflow_config


def send_pending_action_reminders() -> int:
    """Send reminder notifications for requests awaiting action (HR-UC-021, AFR-079)."""
    cutoff = timezone.now() - timedelta(days=2)
    reminder_count = 0

    # 1. Pending leaves
    stale_leaves = LeaveRequest.objects.filter(
        status__in=["pending", "forwarded"],
        created_at__lte=cutoff,
    )
    for leave in stale_leaves:
        send_hr_notification(
            user_id=leave.user_id,
            title="Pending Leave Reminder",
            message=f"Your {leave.leave_type} leave request is awaiting action from {leave.current_authority_role.upper()}.",
            category="reminder",
            link=f"/hr/leaves/{leave.id}",
        )
        reminder_count += 1

    # 2. Pending LTC verification / approval
    stale_ltc = LtcRequest.objects.filter(
        status__in=["submitted", "pending_approval"],
        created_at__lte=cutoff,
    )
    for ltc in stale_ltc:
        send_hr_notification(
            user_id=ltc.user_id,
            title="LTC Claim Reminder",
            message=f"Your LTC {ltc.request_type} claim is currently pending action ({ltc.status}).",
            category="reminder",
            link=f"/hr/ltc/{ltc.id}",
        )
        reminder_count += 1

    # 3. Pending CPDA
    stale_cpda = CpdaRequest.objects.filter(
        status__in=["submitted", "pending_approval"],
        created_at__lte=cutoff,
    )
    for cpda in stale_cpda:
        send_hr_notification(
            user_id=cpda.user_id,
            title="CPDA Claim Reminder",
            message=f"Your CPDA {cpda.request_type} claim is currently pending action ({cpda.status}).",
            category="reminder",
            link=f"/hr/cpda/{cpda.id}",
        )
        reminder_count += 1

    return reminder_count


def send_deadline_notifications() -> int:
    """Alert employees of upcoming appraisal window closures (HR-UC-022, AFR-080)."""
    window_cfg = get_workflow_config("appraisal_window")
    if not window_cfg or not window_cfg.get("active"):
        return 0

    end_str = window_cfg.get("end_date")
    academic_year = window_cfg.get("academic_year", "")
    if not end_str:
        return 0

    end_date = date.fromisoformat(str(end_str))
    days_left = (end_date - date.today()).days
    if not (0 <= days_left <= 7):
        return 0  # Only notify within the final 7 days

    # Find active employees who have not yet submitted
    submitted_user_ids = set(
        AppraisalSubmission.objects.filter(
            academic_year=academic_year,
            status__in=["submitted", "under_review", "finalized"],
        ).values_list("user_id", flat=True)
    )

    eligible_records = EmployeeServiceRecord.objects.filter(is_active=True).exclude(
        user_id__in=submitted_user_ids
    )

    count = 0
    for rec in eligible_records:
        send_hr_notification(
            user_id=rec.user_id,
            title="Appraisal Deadline Approaching",
            message=f"Reminder: Annual appraisal submission for {academic_year} closes in {days_left} day(s) on {end_date}.",
            category="policy",
            link="/hr/appraisals",
        )
        count += 1

    return count
