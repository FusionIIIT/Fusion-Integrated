"""Application operations for Employee Leave Management."""
from datetime import date

from django.db import transaction
from django.utils import timezone

from modules.elm.models import LeaveApplication
from modules.elm.services.policy import (
    PolicyValidationError,
    SUPPORTED_LEAVE_TYPES,
    count_leave_days,
    LeaveInterval,
    intervals_overlap,
)


class LeaveApplicationError(Exception):
    """Raised when a leave application cannot be processed."""


ACTIVE_OVERLAP_STATUSES = (
    LeaveApplication.Status.SUBMITTED,
    LeaveApplication.Status.PENDING_APPROVAL,
    LeaveApplication.Status.APPROVED,
    LeaveApplication.Status.EXTENSION_REQUESTED,
)


def _clean_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise LeaveApplicationError(f"{label} is required.")
    return value.strip()


@transaction.atomic
def submit_leave(
    *,
    employee_id: str,
    leave_type: str,
    start_date: date,
    end_date: date,
    reason: str,
    start_half: str = "",
    end_half: str = "",
    excluded_dates=(),
) -> LeaveApplication:
    """Validate and create a leave application; balance/calendar checks are external."""
    employee_id = _clean_text(employee_id, "Employee ID")
    leave_type = _clean_text(leave_type, "Leave type").upper()
    reason = _clean_text(reason, "A reason for leave")
    if leave_type not in SUPPORTED_LEAVE_TYPES:
        raise LeaveApplicationError(f"Unsupported leave category: {leave_type}.")
    try:
        days_requested = count_leave_days(
            leave_type, start_date, end_date, start_half=start_half,
            end_half=end_half, excluded_dates=excluded_dates,
        )
    except (PolicyValidationError, TypeError, AttributeError) as exc:
        raise LeaveApplicationError(str(exc)) from exc
    if days_requested <= 0:
        raise LeaveApplicationError("The selected dates contain no eligible leave days.")

    existing = LeaveApplication.objects.filter(
        employee_id=employee_id,
        status__in=ACTIVE_OVERLAP_STATUSES,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    candidate = LeaveInterval(
        start_date, end_date, leave_type,
        LeaveApplication.Status.SUBMITTED, start_half, end_half,
    )
    for item in existing:
        other = LeaveInterval(
            item.start_date, item.end_date, item.leave_type, item.status,
            item.start_half, item.end_half,
        )
        if intervals_overlap(candidate, other):
            raise LeaveApplicationError(
                f"Leave dates overlap an existing active application ({item.pk})."
            )

    return LeaveApplication.objects.create(
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        start_half=start_half,
        end_half=end_half,
        requested_days=days_requested,
        status=LeaveApplication.Status.SUBMITTED,
        submitted_at=timezone.now(),
    )


@transaction.atomic
def decide_leave(
    *,
    application_id,
    approver_id: str,
    approve: bool,
    decision_note: str = "",
) -> LeaveApplication:
    """Record a decision only while the application is awaiting a decision."""
    application = LeaveApplication.objects.select_for_update().get(
        pk=application_id
    )
    if application.status not in {
        LeaveApplication.Status.SUBMITTED,
        LeaveApplication.Status.PENDING_APPROVAL,
    }:
        raise LeaveApplicationError("Only pending applications can receive a decision.")
    approver_id = _clean_text(approver_id, "Approver ID")
    if not isinstance(approve, bool):
        raise LeaveApplicationError("Decision must be a boolean.")
    application.approver_id = approver_id
    application.decision_note = decision_note.strip() if isinstance(decision_note, str) else ""
    application.status = (
        LeaveApplication.Status.APPROVED if approve
        else LeaveApplication.Status.REJECTED
    )
    application.decided_at = timezone.now()
    application.save(update_fields=[
        "approver_id", "decision_note", "status", "decided_at", "updated_at",
    ])
    return application


@transaction.atomic
def transition_leave(*, application_id, actor_id: str, action: str, note: str = ""):
    """Apply safe owner/authorized workflow transitions; permission is checked by API."""
    application = LeaveApplication.objects.select_for_update().get(pk=application_id)
    actor_id = _clean_text(actor_id, "Actor ID")
    allowed = {
        "withdraw": ({LeaveApplication.Status.SUBMITTED,
                      LeaveApplication.Status.PENDING_APPROVAL},
                     LeaveApplication.Status.WITHDRAWN),
        "cancel": ({LeaveApplication.Status.APPROVED},
                   LeaveApplication.Status.CANCELLED),
        "extend": ({LeaveApplication.Status.APPROVED},
                   LeaveApplication.Status.EXTENSION_REQUESTED),
        "resume": ({LeaveApplication.Status.APPROVED},
                   LeaveApplication.Status.RESUMED),
    }
    if action not in allowed:
        raise LeaveApplicationError("Unsupported leave action.")
    from_statuses, target = allowed[action]
    if application.status not in from_statuses:
        raise LeaveApplicationError(
            f"Cannot {action} a leave application in '{application.status}' status."
        )
    application.status = target
    # Preserve a decision note/audit hint without overwriting an existing note.
    stamp = (
        f"[{timezone.now().isoformat()}] {action} by {actor_id}: "
        f"{note.strip()}"
    ).strip()
    application.decision_note = (
        f"{application.decision_note}\n{stamp}".strip()
        if application.decision_note else stamp
    )
    application.save(update_fields=["status", "decision_note", "updated_at"])
    return application
