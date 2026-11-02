"""Hostel complaint management services (3.5, CFR-HM-014, BR-HM-015, CW-HM-02)."""

from django.db import transaction
from django.utils import timezone
from ..domain.constants import ComplaintStatus
from ..domain.errors import HostelDomainError, InactiveHostelError
from ..domain.state_machine import WorkflowStateMachine
from ..models import Hostel, HostelComplaint, HostelRoleBinding
from .notification_service import create_notification


@transaction.atomic
def submit_complaint(
    student_user_id: int,
    student_roll_number: str,
    student_name: str,
    hostel_id: int,
    category: str,
    title: str,
    description: str,
    room_number: str = "",
    attachment_url: str = "",
) -> HostelComplaint:
    """Student submits hostel-related complaint (HM-UC-017, BR-HM-015)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if not hostel.is_active:
        raise InactiveHostelError(hostel.name)

    complaint = HostelComplaint.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        student_roll_number=student_roll_number.strip(),
        student_name=student_name.strip(),
        room_number=room_number.strip(),
        category=category,
        title=title.strip(),
        description=description.strip(),
        attachment_url=attachment_url.strip(),
        status=ComplaintStatus.SUBMITTED.value,
    )

    create_notification(
        recipient_user_id=student_user_id,
        event_type="complaint_submitted",
        title="Hostel Complaint Submitted",
        message=f"Complaint #{complaint.id} ({title}) has been submitted.",
        reference_id=str(complaint.id),
    )
    return complaint


@transaction.atomic
def update_complaint_status(
    handler_user_id: int,
    complaint_id: int,
    status: str,  # 'in_progress', 'resolved', 'escalated'
    action_taken: str = "",
    escalate_to_warden: bool = False,
    escalation_reason: str = "",
) -> HostelComplaint:
    """Caretaker/Warden updates complaint status, resolves, or escalates (HM-UC-018, CW-HM-02)."""
    complaint = HostelComplaint.objects.select_for_update().select_related("hostel").filter(id=complaint_id).first()
    if not complaint:
        raise HostelDomainError(f"Complaint {complaint_id} not found.", code="not_found")

    target_status = ComplaintStatus.ESCALATED.value if escalate_to_warden else status
    WorkflowStateMachine.validate_complaint_transition(complaint.status, target_status)

    complaint.status = target_status
    if action_taken:
        complaint.action_taken = action_taken.strip()
    complaint.caretaker_user_id = handler_user_id

    if target_status == ComplaintStatus.RESOLVED.value:
        complaint.resolved_at = timezone.now()

    if escalate_to_warden:
        complaint.escalated_to_warden = True
        complaint.escalated_at = timezone.now()
        complaint.escalation_reason = escalation_reason.strip()

        # Notify Wardens of this hostel
        warden_user_ids = HostelRoleBinding.objects.filter(
            hostel=complaint.hostel, role="warden", is_active=True
        ).values_list("user_id", flat=True)
        for w_id in warden_user_ids:
            create_notification(
                recipient_user_id=w_id,
                event_type="complaint_escalated",
                title="Complaint Escalated",
                message=f"Complaint #{complaint.id} in {complaint.hostel.name} has been escalated to Warden.",
                reference_id=str(complaint.id),
            )

    complaint.save()

    create_notification(
        recipient_user_id=complaint.student_user_id,
        event_type="complaint_status_updated",
        title="Complaint Status Updated",
        message=f"Your complaint #{complaint.id} is now '{target_status}'.",
        reference_id=str(complaint.id),
    )

    return complaint
