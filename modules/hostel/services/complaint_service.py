"""Complaint services (CFR-HM-015..018, BW-HM-04/05, CW-HM-02, BR-HM-015..017)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.constants import (
    ComplaintCategory,
    ComplaintSeverity,
    ComplaintStatus,
    NotificationEventType,
)
from modules.hostel.domain.errors import ValidationError
from modules.hostel.domain.state_machine import COMPLAINT_TRANSITIONS, validate_transition
from modules.hostel.models import Hostel, HostelComplaint, HostelRoleBinding
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def submit_complaint(
    student_user_id: int,
    hostel_id: int,
    title: str,
    description: str,
    location: str,
    category: str = ComplaintCategory.ELECTRICAL.value,
    severity: str = ComplaintSeverity.MEDIUM.value,
) -> HostelComplaint:
    """CFR-HM-015, HM-UC-017, BR-HM-015: Student submits complaint."""
    if not title or not title.strip():
        raise ValidationError("Title is required for complaint")
    if not description or not description.strip():
        raise ValidationError("Description is required for complaint")
    if not location or not location.strip():
        raise ValidationError("Location is required for complaint")

    hostel = Hostel.objects.get(id=hostel_id)

    return HostelComplaint.objects.create(
        student_user_id=student_user_id,
        hostel=hostel,
        category=category,
        title=title.strip(),
        description=description.strip(),
        location=location.strip(),
        severity=severity,
        status=ComplaintStatus.OPEN.value,
    )


@transaction.atomic
def update_complaint_status(
    complaint_id: int,
    target_status: str,
    actor_role: str,
    actor_user_id: int | None = None,
    assigned_worker: str = "",
    resolution_notes: str = "",
) -> HostelComplaint:
    """CFR-HM-016, 018, HM-UC-018, BW-HM-04/05, CW-HM-02: Review, resolve, or escalate complaint."""
    complaint = HostelComplaint.objects.select_for_update().get(id=complaint_id)

    validate_transition(
        transitions=COMPLAINT_TRANSITIONS,
        current_status=complaint.status,
        target_status=target_status,
        actor_role=actor_role,
    )

    complaint.status = target_status

    if assigned_worker:
        complaint.assigned_worker = assigned_worker.strip()

    if target_status == ComplaintStatus.ESCALATED.value:
        complaint.escalated_to_warden = True
        # Notify warden(s)
        wardens = HostelRoleBinding.objects.filter(
            hostel=complaint.hostel, role="warden", is_active=True
        ).values_list("user_id", flat=True)
        for w_id in wardens:
            emit_notification(
                recipient_user_id=w_id,
                title="Complaint Escalated",
                message=f"Complaint #{complaint.id} in {complaint.hostel.code} has been escalated.",
                event_type=NotificationEventType.COMPLAINT_ESCALATED,
                link="/hostel/complaints",
            )

    if target_status == ComplaintStatus.RESOLVED.value:
        complaint.resolved_by_user_id = actor_user_id
        complaint.resolved_at = timezone.now()
        complaint.resolution_notes = resolution_notes.strip()
        emit_notification(
            recipient_user_id=complaint.student_user_id,
            title="Complaint Resolved",
            message=f"Your complaint #{complaint.id} ({complaint.title}) has been resolved.",
            event_type=NotificationEventType.COMPLAINT_STATUS_CHANGED,
            link="/hostel/complaints",
        )

    complaint.save(
        update_fields=[
            "status",
            "assigned_worker",
            "escalated_to_warden",
            "resolved_by_user_id",
            "resolved_at",
            "resolution_notes",
            "updated_at",
        ]
    )

    return complaint
