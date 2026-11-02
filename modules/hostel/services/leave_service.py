"""Leave request and decision services (CFR-HM-012..014, BW-HM-02/03, CW-HM-01, BR-HM-013)."""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.constants import LeaveStatus, LeaveType, NotificationEventType
from modules.hostel.domain.errors import ValidationError
from modules.hostel.domain.state_machine import LEAVE_TRANSITIONS, validate_transition
from modules.hostel.models import Hostel, HostelLeave
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def submit_leave_request(
    student_user_id: int,
    hostel_id: int,
    from_date: date,
    to_date: date,
    reason: str,
    leave_type: str = LeaveType.HOME.value,
    destination: str = "",
    emergency_contact: str = "",
) -> HostelLeave:
    """CFR-HM-012, HM-UC-014: Student submits leave request."""
    if from_date > to_date:
        raise ValidationError("Leave 'from_date' cannot be after 'to_date'")
    if not reason or not reason.strip():
        raise ValidationError("Reason is required for leave request")

    hostel = Hostel.objects.get(id=hostel_id)

    return HostelLeave.objects.create(
        student_user_id=student_user_id,
        hostel=hostel,
        leave_type=leave_type,
        from_date=from_date,
        to_date=to_date,
        reason=reason.strip(),
        destination=destination.strip(),
        emergency_contact=emergency_contact.strip(),
        status=LeaveStatus.PENDING.value,
    )


@transaction.atomic
def decide_leave_request(
    leave_id: int,
    decision: str,  # 'approved' or 'rejected'
    caretaker_user_id: int | None = None,
    remarks: str = "",
) -> HostelLeave:
    """CFR-HM-013, HM-UC-015, BW-HM-02/03, CW-HM-01: Caretaker decides leave request."""
    leave = HostelLeave.objects.select_for_update().get(id=leave_id)

    validate_transition(
        transitions=LEAVE_TRANSITIONS,
        current_status=leave.status,
        target_status=decision,
        actor_role="caretaker",
    )

    leave.status = decision
    leave.decided_by_user_id = caretaker_user_id
    leave.decided_at = timezone.now()
    leave.decision_remarks = remarks.strip()
    leave.save(
        update_fields=[
            "status",
            "decided_by_user_id",
            "decided_at",
            "decision_remarks",
            "updated_at",
        ]
    )

    emit_notification(
        recipient_user_id=leave.student_user_id,
        title=f"Hostel Leave {decision.capitalize()}",
        message=f"Leave {leave.from_date} to {leave.to_date} was {decision}. Remarks: {remarks}",
        event_type=NotificationEventType.LEAVE_STATUS_CHANGED,
        link="/hostel/leaves",
    )

    return leave
